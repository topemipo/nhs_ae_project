USE master;
GO

IF DB_ID('nhs_ae_warehouse') IS NULL
BEGIN
    CREATE DATABASE nhs_ae_warehouse;
    PRINT 'Created database nhs_ae_warehouse';
END
ELSE
BEGIN
    PRINT 'Database nhs_ae_warehouse already exists';
END;
GO