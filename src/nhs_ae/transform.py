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
    params = {"batch_month": batch_month}

    with engine.begin() as conn:
        # Move 1: build a temp table of the Org Codes whose attributes changed
        conn.execute(text("""
            DROP TABLE IF EXISTS #changed;
            CREATE TABLE #changed (
                Org_Code     NVARCHAR(50) PRIMARY KEY,
                Provider_Key INT NOT NULL
            );

            INSERT INTO #changed (Org_Code, Provider_Key)
            SELECT stg.Org_Code, dim.Provider_Key
            FROM dbo.vStaging_Provider AS stg
            INNER JOIN dbo.Dim_Provider AS dim
                ON dim.Org_Code = stg.Org_Code
            WHERE dim.Is_Current = 1
              AND (
                    stg.Parent_Org IS DISTINCT FROM dim.Parent_Org
                 OR stg.Org_Name  IS DISTINCT FROM dim.Org_Name
              );
        """))
        changed_count = conn.execute(text("SELECT COUNT(*) FROM #changed")).scalar()
        print(f"  Move 1: {changed_count} changed provider(s) identified.")

        # Move 2: close the current version of those changed providers
        result = conn.execute(text("""
            UPDATE dim
            SET dim.Valid_To   = :batch_month,
                dim.Is_Current = 0
            FROM dbo.Dim_Provider AS dim
            INNER JOIN #changed AS c
                ON c.Provider_Key = dim.Provider_Key;
        """), params)
        print(f"  Move 2: {result.rowcount} version(s) closed.")

        # Move 3: open a new version for those same changed providers
        # (uses Org_Code, not Provider_Key: that key is now closed)
        result = conn.execute(text("""
            INSERT INTO dbo.Dim_Provider
                (Org_Code, Parent_Org, Org_Name,
                 Valid_From, Valid_To, Is_Current,
                 Reason_Status, Last_Seen_Month)
            SELECT
                stg.Org_Code,
                stg.Parent_Org,
                stg.Org_Name,
                :batch_month,
                '9999-12-31',
                1,
                'Attribute change',
                :batch_month
            FROM dbo.vStaging_Provider AS stg
            INNER JOIN #changed AS c
                ON c.Org_Code = stg.Org_Code;
        """), params)
        print(f"  Move 3: {result.rowcount} new version(s) opened.")
        
        # Move 4: insert brand-new providers (Org Code not in the dimension at all)
        result = conn.execute(text("""
            INSERT INTO dbo.Dim_Provider
                (Org_Code, Parent_Org, Org_Name,
                 Valid_From, Valid_To, Is_Current,
                 Reason_Status, Last_Seen_Month)
            SELECT
                stg.Org_Code,
                stg.Parent_Org,
                stg.Org_Name,
                :batch_month,
                '9999-12-31',
                1,
                'New provider',
                :batch_month
            FROM dbo.vStaging_Provider AS stg
            WHERE NOT EXISTS (
                SELECT 1
                FROM dbo.Dim_Provider AS dim
                WHERE dim.Org_Code = stg.Org_Code
            );
        """), params)
        print(f"  Move 4: {result.rowcount} new provider(s) inserted.")

        # Move 5: handle reapperance 
        result = conn.execute(text("""
            INSERT INTO dbo.Dim_Provider
                (Org_Code, Parent_Org, Org_Name,
                 Valid_From, Valid_To, Is_Current,
                 Reason_Status, Last_Seen_Month)
            SELECT
                stg.Org_Code,
                stg.Parent_Org,
                stg.Org_Name,
                :batch_month,
                '9999-12-31',
                1,
                'Reappeared',
                :batch_month
            FROM dbo.vStaging_Provider AS stg
            WHERE NOT EXISTS (
                    SELECT 1 FROM dbo.Dim_Provider AS dim
                    WHERE dim.Org_Code = stg.Org_Code
                      AND dim.Is_Current = 1
                  )
              AND EXISTS (
                    SELECT 1 FROM dbo.Dim_Provider AS dim
                    WHERE dim.Org_Code = stg.Org_Code
                  );
        """), params)
        print(f"  Move 5: {result.rowcount} reappeared provider(s) reopened.")

        # Move 6: close providers absent for two consecutive months
        result = conn.execute(text("""
            UPDATE dim
            SET dim.Valid_To   = :batch_month,
                dim.Is_Current = 0
            FROM dbo.Dim_Provider AS dim
            WHERE dim.Is_Current = 1
              AND NOT EXISTS (
                    SELECT 1
                    FROM dbo.vStaging_Provider AS stg
                    WHERE stg.Org_Code = dim.Org_Code
              )
              AND DATEDIFF(MONTH, dim.Last_Seen_Month, :batch_month) >= 2;
        """), params)
        print(f"  Move 6: {result.rowcount} absent version(s) closed.")

        # Move 7: update Last_Seen_Month for every provider present this month
        result = conn.execute(text("""
            UPDATE dim
            SET dim.Last_Seen_Month = :batch_month
            FROM dbo.Dim_Provider AS dim
            INNER JOIN dbo.vStaging_Provider AS stg
                ON stg.Org_Code = dim.Org_Code
            WHERE dim.Is_Current = 1
            AND dim.Last_Seen_Month <> :batch_month;
        """), params)
        print(f"  Move 7: {result.rowcount} present provider(s) last-seen updated.")

