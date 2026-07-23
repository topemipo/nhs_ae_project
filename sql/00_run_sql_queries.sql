USE [nhs_ae_warehouse];
GO

SELECT Last_Seen_Month, COUNT(*) FROM dbo.Dim_Provider GROUP BY Last_Seen_Month;