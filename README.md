```
nhs-ae-warehouse/
├── data/
│   └── raw/                     the twelve CSVs, renamed 2025-01.csv ... (source, read-only)
├── sql/
│   ├── 01_create_database.sql
│   ├── 02_create_staging.sql
│   ├── 03_create_dim_date.sql
│   ├── 04_create_dim_provider.sql
│   └── 05_create_fact_ae_monthly.sql
├── src/
│   └── nhs_ae/                  (whatever you name the package)
│       ├── __init__.py
│       ├── config.py            reads connection details from the environment
│       ├── db.py                builds the SQLAlchemy engine
│       ├── staging.py           Phase 1: clear staging, derive month, verify, load one file
│       └── transform.py         Phase 2: SCD2 into Dim_Provider, then load the fact
├── scripts/
│   └── smoke_test.py            the connection check you already wrote
├── reports/
│   └── ae_dashboard.pbix        (see the note below on whether this belongs in git)
├── docs/
│   └── design-decisions-phase-0-and-1.md
├── .env                         (gitignored) the secret you just moved out of the code
├── .env.example                 the same keys with the values blanked, safe to commit
├── .gitignore
├── requirements.txt
└── README.md
```

```
set -a
source .env
set +a
python3 create_warehouse_db.py
```