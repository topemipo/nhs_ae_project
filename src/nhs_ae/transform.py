from datetime import date
from sqlalchemy import text


def get_batch_month(engine):
    # read the single reporting month currently in staging
    with engine.connect() as conn:
        months = conn.execute(
            text("SELECT DISTINCT Report_Month FROM dbo.Staging_AE_Monthly")
        ).scalars().all()

    if len(months) != 1:
        raise ValueError(f"Expected one month in staging, found {len(months)}: {months}")

    year, month = months[0].split("-")        # "2025-04" -> "2025", "04"
    return date(int(year), int(month), 1)     # date(2025, 4, 1)
    # confirm there is exactly one, then return it as a first-of-month date


def ensure_month_in_dim_date(engine, month_start):
    # derive the parts a month row needs from that date
    # insert the row only if the month is not already present (idempotent)
    MONTH_NAMES = ["", "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December"]
    
    month_sequence = month_start.year * 12 + month_start.month   # 2025*12 + 4 = 24304

    params = {
        "month_start": month_start,
        "month_sequence": month_sequence,
        "calendar_year": month_start.year,
        "month_number": month_start.month,
        "month_name": MONTH_NAMES[month_start.month],
    }

    insert_sql = text("""
        INSERT INTO dbo.Dim_Date
            (Month_Start, Month_Sequence, Calendar_Year, Month_Number, Month_Name)
        SELECT :month_start, :month_sequence, :calendar_year, :month_number, :month_name
        WHERE NOT EXISTS (
            SELECT 1 FROM dbo.Dim_Date WHERE Month_Start = :month_start
        );
    """)

    with engine.begin() as conn:
        conn.execute(insert_sql, params)


def assert_provider_grain(engine):
    # find any Org Code that appears more than once in this month's staging
    # if any are found, stop: the SCD2 joins assume one row per provider
    with engine.connect() as conn:
        dupes = conn.execute(text("""
            SELECT [Org Code] AS org_code, COUNT(*) AS n
            FROM dbo.Staging_AE_Monthly
            GROUP BY [Org Code]
            HAVING COUNT(*) > 1
        """)).all()

    if dupes:
        raise ValueError(
            f"Staging is not at provider grain; these Org Codes repeat: {dupes}"
        )
    

def load_dim_provider_scd2(engine, batch_month):
    close_changed = text("""
        UPDATE dim
        SET
            dim.Valid_To   = :batch_month,
            dim.Is_Current = 0
        FROM dbo.Dim_Provider AS dim
        INNER JOIN dbo.vStaging_Provider AS stg
            ON stg.Org_Code = dim.Org_Code
        WHERE dim.Is_Current = 1
          AND (
                stg.Parent_Org IS DISTINCT FROM dim.Parent_Org
             OR stg.Org_Name  IS DISTINCT FROM dim.Org_Name
          );
    """)

    with engine.begin() as conn:
        # Move 2a: close the old version of any provider whose attributes changed
        result = conn.execute(close_changed, {"batch_month": batch_month})
        print(f"  Closed {result.rowcount} changed version(s).")

        # Move 2b: open a new version for those changed providers  (next)

        # Move 2c: insert brand-new providers (no current version)

        # Move 3:  close providers absent for two consecutive months

        # Move 4:  update Last_Seen_Month for providers present this month