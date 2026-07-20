USE [nhs_ae_warehouse];
GO

SELECT MIN(Provider_Key) AS min_key, MAX(Provider_Key) AS max_key,
       COUNT(DISTINCT Provider_Key) AS distinct_keys
FROM dbo.Dim_Provider;