"""Extract + Load step: generate synthetic mortgage origination and servicing
files, validate them, and land them into the DuckDB `raw` schema.

In production the CSV generation is replaced by an SFTP/S3 pull; the
validation and idempotent load logic is the same.

    python ingestion/generate_and_load.py --db warehouse.duckdb --loans 5000 --months 24
"""
import argparse
import csv
import random
from datetime import date
from pathlib import Path

import duckdb

STATES = ["TX", "CA", "FL", "NY", "IL", "GA", "AZ", "NC", "WA", "CO"]
PRODUCTS = [("30Y_FIXED", 360), ("15Y_FIXED", 180), ("7_1_ARM", 360)]
PURPOSES = ["PURCHASE", "REFI_RATE_TERM", "REFI_CASH_OUT"]


def add_months(d: date, n: int) -> date:
    y, m = divmod(d.month - 1 + n, 12)
    return date(d.year + y, m + 1, 1)


def monthly_payment(principal: float, annual_rate: float, term: int) -> float:
    r = annual_rate / 12
    return principal * r / (1 - (1 + r) ** -term)


def generate(out_dir: Path, n_loans: int, n_months: int, seed: int = 7) -> tuple[Path, Path]:
    random.seed(seed)
    out_dir.mkdir(parents=True, exist_ok=True)
    loans_path, pays_path = out_dir / "loan_origination.csv", out_dir / "loan_servicing.csv"
    start = date(2024, 1, 1)

    with loans_path.open("w", newline="") as lf, pays_path.open("w", newline="") as pf:
        lw, pw = csv.writer(lf), csv.writer(pf)
        lw.writerow(["loan_id", "borrower_id", "origination_date", "product", "term_months", "purpose",
                     "property_state", "original_balance", "interest_rate", "credit_score", "ltv", "dti"])
        pw.writerow(["loan_id", "reporting_month", "scheduled_payment", "actual_payment",
                     "unpaid_principal_balance", "days_past_due"])

        for i in range(1, n_loans + 1):
            product, term = random.choice(PRODUCTS)
            orig = add_months(start, random.randint(0, 6))
            bal = round(random.uniform(120_000, 850_000), -2)
            rate = round(random.uniform(0.055, 0.079), 4)
            fico = int(min(850, max(580, random.gauss(735, 45))))
            risk = (800 - fico) / 220  # 0 (good) .. ~1 (risky)
            loan_id = f"L{i:07d}"
            lw.writerow([loan_id, f"B{random.randint(1, n_loans):07d}", orig.isoformat(), product, term,
                         random.choice(PURPOSES), random.choice(STATES), bal, rate, fico,
                         round(random.uniform(0.55, 0.97), 3), round(random.uniform(0.18, 0.49), 3)])

            pmt = monthly_payment(bal, rate, term)
            upb, dpd = bal, 0
            for m in range(n_months):
                month = add_months(orig, m + 1)
                if month > add_months(start, n_months):
                    break
                if dpd == 0 and random.random() < 0.012 * (1 + 3 * risk):
                    paid = 0.0
                elif dpd > 0 and random.random() < 0.55:
                    paid = 0.0
                else:
                    paid = pmt
                if paid > 0:
                    interest = upb * rate / 12
                    upb = max(0.0, upb - (paid - interest))
                    dpd = 0 if random.random() < 0.8 else dpd
                else:
                    dpd += 30
                pw.writerow([loan_id, month.isoformat(), round(pmt, 2), round(paid, 2), round(upb, 2), dpd])
                if dpd >= 180:  # charged off / foreclosure: stop reporting
                    break
    return loans_path, pays_path


def validate(con: duckdb.DuckDBPyConnection, table: str, key_cols: list[str], not_null: list[str]) -> None:
    """Fail fast before anything downstream reads bad data."""
    keys = ", ".join(key_cols)
    dups = con.execute(f"select count(*) from (select {keys} from {table} group by {keys} having count(*) > 1)").fetchone()[0]
    if dups:
        raise ValueError(f"{table}: {dups} duplicate keys on ({keys})")
    for col in not_null:
        nulls = con.execute(f"select count(*) from {table} where {col} is null").fetchone()[0]
        if nulls:
            raise ValueError(f"{table}: {nulls} nulls in {col}")


def load(db: str, loans_csv: Path, pays_csv: Path) -> dict[str, int]:
    con = duckdb.connect(db)
    con.execute("create schema if not exists raw")
    con.execute("create schema if not exists staging_load")
    con.execute(f"create or replace table staging_load.loans as select *, current_timestamp as _loaded_at from read_csv_auto('{loans_csv}')")
    con.execute(f"create or replace table staging_load.payments as select *, current_timestamp as _loaded_at from read_csv_auto('{pays_csv}')")

    validate(con, "staging_load.loans", ["loan_id"], ["loan_id", "origination_date", "original_balance"])
    validate(con, "staging_load.payments", ["loan_id", "reporting_month"], ["loan_id", "reporting_month"])

    # Atomic swap so readers never see a half-loaded table.
    con.execute("begin")
    con.execute("create or replace table raw.loan_origination as select * from staging_load.loans")
    con.execute("create or replace table raw.loan_servicing as select * from staging_load.payments")
    con.execute("commit")
    counts = {
        "loan_origination": con.execute("select count(*) from raw.loan_origination").fetchone()[0],
        "loan_servicing": con.execute("select count(*) from raw.loan_servicing").fetchone()[0],
    }
    con.close()
    return counts


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--db", default="warehouse.duckdb")
    p.add_argument("--landing", default="data/landing")
    p.add_argument("--loans", type=int, default=5000)
    p.add_argument("--months", type=int, default=24)
    a = p.parse_args()
    loans, pays = generate(Path(a.landing), a.loans, a.months)
    print(load(a.db, loans, pays))


if __name__ == "__main__":
    main()
