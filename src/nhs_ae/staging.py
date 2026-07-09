from pathlib import Path
import pandas as pd
from datetime import datetime
from sqlalchemy import text

def load_month(csv_path, engine):
    # Step 1: clear the staging table, unconditionally
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE TABLE dbo.Staging_AE_Monthly;"))

    # Step 2: read the reporting month claimed by the filename
    claimed_month = Path(csv_path).stem   # "data/raw/2025-05.csv" -> "2025-05"

    # Step 3: read the CSV into a DataFrame
    df = pd.read_csv(csv_path)

    # Step 4: derive the month from Period, keep the original, verify against the filename
    # 4a: the file should describe one month, so Period should hold a single value
    periods = df["Period"].unique()
    if len(periods) != 1:
        raise ValueError(f"Expected one Period in {csv_path}, found {len(periods)}: {periods}")
    period_value = periods[0]                      # "MSitAE-MAY-2025"
    # 4b: turn that string into a real month-start date
    month_year = period_value.split("-", 1)[1]                # "MAY-2025"
    parsed = datetime.strptime(month_year.title(), "%B-%Y")   # reads the full month name
    report_month = f"{parsed:%Y-%m}"                          # "2025-05", month only
    # 4c: store it as a new column, leaving Period untouched
    df["Report_Month"] = report_month       # every row gets "2025-05"
    # 4d: the file's own month must match what the filename claimed
    if f"{report_month:%Y-%m}" != claimed_month:
        raise ValueError(
            f"Filename claims {claimed_month} but Period says {report_month:%Y-%m}"
        )

    # Step 5: write the rows into the now-empty staging table
    with engine.begin() as conn:
        df.to_sql(
            "Staging_AE_Monthly",
            conn,
            schema="dbo",
            if_exists="append",
            index=False,
        )