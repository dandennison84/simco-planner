from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any, Dict, Iterable, List, Mapping, Tuple
import json

import yaml
from jsonschema import Draft7Validator


# =============================================================================
# Models
# =============================================================================

@dataclass(frozen=True)
class TableContract:
    path: Path
    table: str
    surface: str
    version: int
    intent: str
    presence: Mapping[str, bool]
    keys: Tuple[str, ...]
    fields: Mapping[str, Mapping[str, Any]]

@dataclass(frozen=True)
class LookupRule:
    ui_table: str
    ui_column: str
    ref_table: str
    ref_key_field: str
    ref_label_field: str
    excel: Mapping[str, str]

@dataclass(frozen=True)
class LookupContract:
    path: Path
    version: int
    intent: str
    lookups: Tuple[LookupRule, ...]

@dataclass(frozen=True)
class ContractRegistry:
    tables_by_surface: Mapping[str, Mapping[str, TableContract]]
    lookup_contracts: Tuple[LookupContract, ...]


# =============================================================================
# Public API
# =============================================================================

def load_contract_registry(contracts_root: Path) -> ContractRegistry:
    paths = discover_contract_paths(contracts_root)

    loaded = tuple((path, _load_yaml(path)) for path in paths)

    errors: List[str] = []
    tables: List[TableContract] = []
    lookups: List[LookupContract] = []

    for path, doc in loaded:
        kind = str((doc or {}).get("kind", "")).strip()
        if not kind:
            errors.append(f"{path}: missing contract kind")
            continue

        schema_path = _meta_schema_path(contracts_root, kind)
        if not schema_path.exists():
            errors.append(f"{path}: missing meta-schema for kind '{kind}' at {schema_path}")
            continue

        schema_doc = _load_json(schema_path)

        errors.extend(_validate_against_schema(path, doc, schema_doc))

        if kind == "table":
            errors.extend(_validate_table_contract_semantics(path, doc))
            if not errors_for_path(errors, path):
                tables.append(_to_table_contract(path, doc))
        elif kind == "lookup_mapping":
            errors.extend(_validate_lookup_contract_semantics(path, doc))
            if not errors_for_path(errors, path):
                lookups.append(_to_lookup_contract(path, doc))
        else:
            errors.append(f"{path}: unsupported contract kind '{kind}'")

    errors.extend(_validate_unique_table_identity(tables))

    if errors:
        raise ValueError("Contract validation failed:\n" + "\n".join(f"- {e}" for e in errors))

    return _build_registry(tuple(tables), tuple(lookups))


def discover_contract_paths(contracts_root: Path) -> Tuple[Path, ...]:
    return tuple(
        sorted(
            path
            for path in contracts_root.rglob("*.y*ml")
            if "/schema/" not in path.as_posix().replace("\\", "/")
        )
    )


def tables_for_surface(registry: ContractRegistry, surface: str) -> Mapping[str, TableContract]:
    return registry.tables_by_surface.get(surface, {})


def table_contract_to_schema(contract: TableContract) -> Dict[str, Any]:
    return {
        "keys": list(contract.keys),
        "fields": {k: dict(v) for k, v in contract.fields.items()},
    }


def required_table_names(contracts: Mapping[str, TableContract]) -> Tuple[str, ...]:
    return tuple(
        sorted(
            name
            for name, contract in contracts.items()
            if bool(contract.presence.get("required", False))
        )
    )


def required_non_empty_table_names(contracts: Mapping[str, TableContract]) -> Tuple[str, ...]:
    return tuple(
        sorted(
            name
            for name, contract in contracts.items()
            if bool(contract.presence.get("required", False))
            and bool(contract.presence.get("non_empty", False))
        )
    )


def all_lookup_rules(registry: ContractRegistry) -> Tuple[LookupRule, ...]:
    rules: List[LookupRule] = []
    for contract in registry.lookup_contracts:
        rules.extend(contract.lookups)
    return tuple(rules)


def group_lookup_rules_by_ref_table(registry: ContractRegistry) -> Mapping[str, Tuple[LookupRule, ...]]:
    grouped: Dict[str, List[LookupRule]] = {}
    for rule in all_lookup_rules(registry):
        grouped.setdefault(rule.ref_table, []).append(rule)
    return MappingProxyType({k: tuple(v) for k, v in sorted(grouped.items())})


# =============================================================================
# Loading
# =============================================================================

def _load_yaml(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        raise ValueError(f"{path}: contract root must be a mapping")
    return data


def _load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError(f"{path}: json root must be a mapping")
    return data


def _meta_schema_path(contracts_root: Path, kind: str) -> Path:
    name = {
        "table": "table.schema.json",
        "lookup_mapping": "lookup.schema.json",
    }.get(kind, "")
    return contracts_root / "schema" / name


# =============================================================================
# Validation
# =============================================================================

def _validate_against_schema(path: Path, doc: Mapping[str, Any], schema_doc: Mapping[str, Any]) -> List[str]:
    validator = Draft7Validator(schema_doc)
    errors = sorted(validator.iter_errors(doc), key=lambda e: list(e.absolute_path))
    return [f"{path}: {e.message}" for e in errors]


def _validate_table_contract_semantics(path: Path, doc: Mapping[str, Any]) -> List[str]:
    errors: List[str] = []

    table = str(doc.get("table", "")).strip()
    surface = str(doc.get("surface", "")).strip()
    keys = doc.get("keys", [])
    fields = doc.get("fields", {})

    expected_table = path.stem
    expected_surface = path.parent.name

    if table != expected_table:
        errors.append(f"{path}: table '{table}' must match filename '{expected_table}'")

    if surface != expected_surface:
        errors.append(f"{path}: surface '{surface}' must match directory '{expected_surface}'")

    if not isinstance(keys, list):
        errors.append(f"{path}: keys must be a list")
        return errors

    if not isinstance(fields, dict):
        errors.append(f"{path}: fields must be a mapping")
        return errors

    for key in keys:
        if key not in fields:
            errors.append(f"{path}: key '{key}' not found in fields")
            continue
        spec = fields.get(key, {}) or {}
        if not bool(spec.get("required", False)):
            errors.append(f"{path}: key '{key}' must be required")

    for field_name, spec in fields.items():
        spec = spec or {}
        field_type = spec.get("type")
        constraints = spec.get("constraints", {}) or {}

        if field_type not in {"string", "int", "float", "boolean"}:
            errors.append(f"{path}: field '{field_name}' has unsupported type '{field_type}'")

        if constraints and field_type not in {"int", "float"}:
            errors.append(f"{path}: field '{field_name}' has constraints but is not numeric")

    return errors


def _validate_lookup_contract_semantics(path: Path, doc: Mapping[str, Any]) -> List[str]:
    errors: List[str] = []
    lookups = doc.get("lookups", [])
    if not isinstance(lookups, list):
        return [f"{path}: lookups must be a list"]

    seen: set[tuple[str, str]] = set()
    for idx, rule in enumerate(lookups, start=1):
        if not isinstance(rule, dict):
            errors.append(f"{path}: lookups[{idx}] must be a mapping")
            continue
        key = (str(rule.get("ui_table", "")).strip(), str(rule.get("ui_column", "")).strip())
        if key in seen:
            errors.append(f"{path}: duplicate ui lookup mapping for {key}")
        else:
            seen.add(key)
    return errors


def _validate_unique_table_identity(contracts: Iterable[TableContract]) -> List[str]:
    seen: set[tuple[str, str]] = set()
    errors: List[str] = []
    for contract in contracts:
        identity = (contract.surface, contract.table)
        if identity in seen:
            errors.append(f"{contract.path}: duplicate contract identity {identity}")
        else:
            seen.add(identity)
    return errors


def errors_for_path(errors: List[str], path: Path) -> bool:
    prefix = f"{path}:"
    return any(e.startswith(prefix) for e in errors)


# =============================================================================
# Normalization
# =============================================================================

def _to_table_contract(path: Path, doc: Mapping[str, Any]) -> TableContract:
    fields = {
        str(name): MappingProxyType(dict((spec or {})))
        for name, spec in dict(doc["fields"]).items()
    }

    return TableContract(
        path=path,
        table=str(doc["table"]),
        surface=str(doc["surface"]),
        version=int(doc["version"]),
        intent=str(doc["intent"]),
        presence=MappingProxyType(dict(doc["presence"])),
        keys=tuple(str(k) for k in doc["keys"]),
        fields=MappingProxyType(fields),
    )


def _to_lookup_contract(path: Path, doc: Mapping[str, Any]) -> LookupContract:
    rules = tuple(
        LookupRule(
            ui_table=str(rule["ui_table"]),
            ui_column=str(rule["ui_column"]),
            ref_table=str(rule["ref_table"]),
            ref_key_field=str(rule["ref_key_field"]),
            ref_label_field=str(rule["ref_label_field"]),
            excel=MappingProxyType(dict(rule["excel"])),
        )
        for rule in doc["lookups"]
    )
    return LookupContract(
        path=path,
        version=int(doc["version"]),
        intent=str(doc["intent"]),
        lookups=rules,
    )


def _build_registry(
    tables: Tuple[TableContract, ...],
    lookups: Tuple[LookupContract, ...],
) -> ContractRegistry:
    grouped: Dict[str, Dict[str, TableContract]] = {
        "input": {},
        "reference": {},
        "output": {},
        "internal": {},
    }

    for contract in sorted(tables, key=lambda c: (c.surface, c.table)):
        grouped[contract.surface][contract.table] = contract

    frozen = MappingProxyType(
        {surface: MappingProxyType(dict(table_map)) for surface, table_map in grouped.items()}
    )

    return ContractRegistry(
        tables_by_surface=frozen,
        lookup_contracts=tuple(sorted(lookups, key=lambda c: c.path.as_posix())),
    )