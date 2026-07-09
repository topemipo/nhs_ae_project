USE [nhs_ae_warehouse];
GO

IF OBJECT_ID('dbo.Staging_AE_Monthly', 'U') IS NOT NULL
    DROP TABLE dbo.Staging_AE_Monthly;
GO

CREATE TABLE dbo.Staging_AE_Monthly (
    -- 1. Dimension columns: who and when
    [Period]      NVARCHAR(50),    -- raw period, kept exactly as it arrived: "MSitAE-MAY-2025"
    [Org Code]    NVARCHAR(50),    -- the business key, e.g. "RAN" or "Y02615"
    [Parent Org]  NVARCHAR(255),   -- watched attribute: a change here opens a new version in Phase 2
    [Org name]    NVARCHAR(255),   -- watched attribute; note the source spells it lowercase "name"
    -- 2. Measure columns: the counts, in their source families
    --      a. attendances by department type
    [A&E attendances Type 1]                              NVARCHAR(50),
    [A&E attendances Type 2]                              NVARCHAR(50),
    [A&E attendances Other A&E Department]                NVARCHAR(50),   -- "Other A&E Department"
    --      b. booked-appointment attendances
    [A&E attendances Booked Appointments Type 1]              NVARCHAR(50),
    [A&E attendances Booked Appointments Type 2]              NVARCHAR(50),
    [A&E attendances Booked Appointments Other Department]    NVARCHAR(50),   -- here just "Other Department"
    --      c. attendances over four hours
    [Attendances over 4hrs Type 1]                        NVARCHAR(50),
    [Attendances over 4hrs Type 2]                        NVARCHAR(50),
    [Attendances over 4hrs Other Department]              NVARCHAR(50),
    --      d. booked-appointment attendances over four hours
    [Attendances over 4hrs Booked Appointments Type 1]            NVARCHAR(50),
    [Attendances over 4hrs Booked Appointments Type 2]            NVARCHAR(50),
    [Attendances over 4hrs Booked Appointments Other Department]  NVARCHAR(50),
    --      e. waits from decision-to-admit to admission
    [Patients who have waited 4-12 hs from DTA to admission]   NVARCHAR(50),   -- source typo "hs", preserved
    [Patients who have waited 12+ hrs from DTA to admission]   NVARCHAR(50),
    --      f. emergency admissions
    [Emergency admissions via A&E - Type 1]                NVARCHAR(50),
    [Emergency admissions via A&E - Type 2]                NVARCHAR(50),
    [Emergency admissions via A&E - Other A&E department]  NVARCHAR(50),   -- lowercase "department" this time
    [Other emergency admissions]                           NVARCHAR(50),             
    -- 3. Derived column: the clean reporting month added in Python 
    [Report_Month]         NVARCHAR(7)   -- "2025-05", built in Python; last column, no comma
);
GO