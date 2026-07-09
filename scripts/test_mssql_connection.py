import os
import pyodbc

SA_PASSWORD = os.environ["MSSQL_SA_PASSWORD"]

# Note the 'TrustServerCertificate=yes' - essential for local Docker testing with modern drivers
conn_str = (
    "DRIVER={ODBC Driver 18 for SQL Server};"
    "SERVER=127.0.0.1,1433;"
    "DATABASE=master;"
    "UID=sa;"
    "PWD=SA_PASSWORD;"
    "TrustServerCertificate=yes;"
)

try:
    print("Attempting to connect via the ODBC stack...")
    conn = pyodbc.connect(conn_str)
    cursor = conn.cursor()
    
    # Run a simple query to see if the server responds
    cursor.execute("SELECT @@VERSION;")
    row = cursor.fetchone()
    
    print("\n✅ Success! The stack is fully alive.")
    print(f"Connected to: {row[0]}")
    
    conn.close()
except Exception as e:
    print("\n❌ Connection failed. Here is the stack trace:")
    print(e)