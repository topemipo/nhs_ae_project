USE [nhs_ae_warehouse];
GO

CREATE OR ALTER VIEW dbo.vStaging_Provider AS
SELECT
    [Org Code]    AS Org_Code,
    [Parent Org]  AS Parent_Org,
    [Org name]    AS Org_Name
FROM dbo.Staging_AE_Monthly;
GO