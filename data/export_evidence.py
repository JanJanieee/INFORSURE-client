import csv
import sqlite3
from datetime import datetime
from pathlib import Path

# Hanapin ang database sa folder kung nasaan ang script
folder = Path(__file__).resolve().parent
db_file = folder / "infosure.db"

if not db_file.is_file():
    raise FileNotFoundError(
        f"Hindi makita ang database: {db_file}"
    )

# May timestamp para hindi mapatungan ang dating export
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
output_file = folder / f"evidence_export_{timestamp}.csv"

# Read-only connection: hindi babaguhin ang database
connection = sqlite3.connect(
    db_file.as_uri() + "?mode=ro",
    uri=True
)

try:
    cursor = connection.execute(
        "SELECT * FROM evidence ORDER BY evidence_id"
    )

    columns = [column[0] for column in cursor.description]
    rows = cursor.fetchall()

    # UTF-8 with BOM para mabasa nang maayos sa Excel
    with output_file.open(
        "x",
        newline="",
        encoding="utf-8-sig"
    ) as file:
        writer = csv.writer(file)
        writer.writerow(columns)
        writer.writerows(rows)

    print(f"Successful! Na-export ang {len(rows)} records.")
    print(f"CSV file: {output_file}")

finally:
    connection.close()