import duckdb
import pytest

from ingestion.generate_and_load import generate, load, monthly_payment, validate


def test_monthly_payment_matches_amortization_formula():
    # $300k, 6%, 30y -> ~$1,798.65
    assert monthly_payment(300_000, 0.06, 360) == pytest.approx(1798.65, abs=0.01)


def test_generate_and_load_counts(tmp_path):
    loans, pays = generate(tmp_path / "landing", n_loans=200, n_months=12)
    counts = load(str(tmp_path / "wh.duckdb"), loans, pays)
    assert counts["loan_origination"] == 200
    assert counts["loan_servicing"] > 200 * 6


def test_load_is_idempotent(tmp_path):
    loans, pays = generate(tmp_path / "landing", n_loans=50, n_months=6)
    db = str(tmp_path / "wh.duckdb")
    first = load(db, loans, pays)
    assert load(db, loans, pays) == first


def test_validate_rejects_duplicate_keys():
    con = duckdb.connect()
    con.execute("create table t as select * from (values ('a'), ('a')) v(id)")
    with pytest.raises(ValueError, match="duplicate"):
        validate(con, "t", ["id"], ["id"])
