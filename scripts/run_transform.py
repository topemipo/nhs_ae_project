from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from dotenv import load_dotenv
load_dotenv()

from nhs_ae.db import get_engine
from nhs_ae.transform import (
    get_batch_month,
    ensure_month_in_dim_date,
    assert_provider_grain,
    load_dim_provider_scd2,
)

def main():
    engine = get_engine()

    # Step 1: work out which month is in staging, and make sure Dim_Date has it
    batch_month = get_batch_month(engine)
    ensure_month_in_dim_date(engine, batch_month)
    print(f"Ensured {batch_month:%Y-%m} is present in Dim_Date.")

    # Step 2: confirm the batch is one row per provider before comparing
    assert_provider_grain(engine)
    print("Staging confirmed at provider grain.")

    # Step 3: SCD2 load into Dim_Provider (moves 1-4 so far)
    print("Running SCD2 load into Dim_Provider...")
    load_dim_provider_scd2(engine, batch_month)
    print("SCD2 load complete.")

if __name__ == "__main__":
    main()
