import os
from sqlalchemy import create_engine
from sqlalchemy.engine import URL


def get_engine():
    # read the password from the environment, failing loudly if it is missing
    password = os.environ["MSSQL_SA_PASSWORD"]

    # assemble the proven ODBC string, now pointed at the warehouse
    odbc_conn_str = (
        "DRIVER={ODBC Driver 18 for SQL Server};"
        "SERVER=127.0.0.1,1433;"
        "DATABASE=nhs_ae_warehouse;"
        "UID=sa;"
        f"PWD={password};"
        "TrustServerCertificate=yes;"
    )
    # hand the string straight to pyodbc via the dialect, untouched
    connection_url = URL.create("mssql+pyodbc", query={"odbc_connect": odbc_conn_str})
    # build the engine once, with batched inserts turned on
    return create_engine(connection_url, fast_executemany=True)