import os
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL

SA_PASSWORD = os.environ["MSSQL_SA_PASSWORD"]  # set via `export`, never hardcoded

DB_NAME = "nhs_ae_warehouse"  # <- your call, rename as you like

# Same proven connection string from testsmoke.py, untouched.
odbc_conn_str = (
    "DRIVER={ODBC Driver 18 for SQL Server};"
    "SERVER=127.0.0.1,1433;"
    "DATABASE=master;"
    "UID=sa;"
    f"PWD={SA_PASSWORD};"
    "TrustServerCertificate=yes;"
)

# odbc_connect tells the mssql+pyodbc dialect to hand this string straight
# to pyodbc.connect() rather than parsing/rebuilding it as a URL.
connection_url = URL.create("mssql+pyodbc", query={"odbc_connect": odbc_conn_str})
engine = create_engine(connection_url)

# CREATE DATABASE can't run inside a transaction in SQL Server -> autocommit.
with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
    exists = conn.execute(
        text("SELECT 1 FROM sys.databases WHERE name = :name"),
        {"name": DB_NAME},
    ).fetchone()

    if exists:
        print(f"Database '{DB_NAME}' already exists — skipping create.")
    else:
        conn.execute(text(f"CREATE DATABASE [{DB_NAME}]"))
        print(f"Created '{DB_NAME}' through the SQLAlchemy engine.")