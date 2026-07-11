from pathlib import Path
import sys

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from nhs_ae.db import get_engine
from nhs_ae.transform import get_batch_month, ensure_month_in_dim_date, assert_provider_grain
load_dotenv()


def main():
    engine = get_engine()

    # Step 1: work out which month is in staging, and make sure Dim_Date has it
    month_start = get_batch_month(engine)
    ensure_month_in_dim_date(engine, month_start)
    print(f"Ensured {month_start:%Y-%m} is present in Dim_Date.")

    # Step 2: confirm the batch is one row per provider before comparing
    assert_provider_grain(engine)
    print("Staging confirmed at provider grain.")


if __name__ == "__main__":
    main()
