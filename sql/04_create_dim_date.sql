USE [nhs_ae_warehouse];
GO

IF OBJECT_ID('dbo.Dim_Date', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.Dim_Date (
        -- 1. The month key: first-of-month DATE, what the fact joins on
        Month_Start   DATE NOT NULL PRIMARY KEY,
        -- 2. A running month number: makes month-gap arithmetic trivial
        Month_Sequence  INT NOT NULL,
        -- 3. Human-friendly parts: year and month, for slicing and labels
        Calendar_Year   INT NOT NULL,
        Month_Number    INT NOT NULL,
        Month_Name      NVARCHAR(20) NOT NULL
    );
END;
GO