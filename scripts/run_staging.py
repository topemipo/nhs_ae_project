from pathlib import Path
import sys

from sqlalchemy import text
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from nhs_ae.db import get_engine
from nhs_ae.staging import load_month

load_dotenv()
RAW_DIR = Path("data/raw")



def main():
    # Step 1: build the engine once, to reuse for the load and the check
    engine = get_engine()
    # Step 2: find the CSV files and put them in chronological order
    files = sorted(RAW_DIR.glob("*.csv"))
    if not files:
        raise FileNotFoundError(f"No CSV files found in {RAW_DIR}")
    # Step 3: for now, load only the first month, to prove the path works
    csv_path = files[1]
    load_month(csv_path, engine)
    # Step 4: read the row count back, to confirm the rows really landed
    with engine.connect() as conn:
        count = conn.execute(
            text("SELECT COUNT(*) FROM dbo.Staging_AE_Monthly")
        ).scalar()
    print(f"Loaded {csv_path.stem}: staging now holds {count} rows.")


if __name__ == "__main__":
    main()
