from pathlib import Path
import csv
import sys

def main():
    # Optional: workbook path passed from VBA
    workbook_path = sys.argv[1] if len(sys.argv) > 1 else None

    root = Path(__file__).resolve().parent.parent

    output_dir = root / "data" / "runtime" / "output"
    output_dir.mkdir(parents=True, exist_ok=True)

    output_file = output_dir / "kpi_summary.csv"

    with output_file.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["KPI", "Value"])
        writer.writerow(["Test", 1])

    print("Engine ran successfully")

if __name__ == "__main__":
    main()