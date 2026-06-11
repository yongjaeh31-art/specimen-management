import os
import sqlite3
from pathlib import Path

from sqlalchemy import create_engine, text


SQLITE_PATH = Path("specimen_routing.db")
TABLES = [
    "app_users",
    "import_batches",
    "orders",
    "order_tests",
    "specimen_arrivals",
    "scan_logs",
    "department_routes",
    "routing_rules",
    "culture_rules",
    "micro_culture_assignments",
]


def read_env_database_url() -> str:
    env_path = Path(".env")
    if not env_path.exists():
        raise SystemExit(".env file was not found. Run switch_to_postgres.ps1 first.")
    for line in env_path.read_text(encoding="utf-8").splitlines():
        if line.startswith("DATABASE_URL="):
            return line.split("=", 1)[1].strip()
    raise SystemExit("DATABASE_URL was not found in .env.")


def main() -> None:
    if not SQLITE_PATH.exists():
        raise SystemExit("specimen_routing.db was not found.")

    database_url = os.getenv("DATABASE_URL") or read_env_database_url()
    if database_url.startswith("sqlite"):
        raise SystemExit("DATABASE_URL still points to SQLite.")

    sqlite_conn = sqlite3.connect(SQLITE_PATH)
    sqlite_conn.row_factory = sqlite3.Row
    pg_engine = create_engine(database_url, future=True)

    with pg_engine.begin() as pg_conn:
        for table in reversed(TABLES):
            pg_conn.execute(text(f"delete from {table}"))

        for table in TABLES:
            rows = sqlite_conn.execute(f"select * from {table}").fetchall()
            if not rows:
                continue
            columns = rows[0].keys()
            quoted_columns = ", ".join(columns)
            values = ", ".join(f":{column}" for column in columns)
            pg_conn.execute(
                text(f"insert into {table} ({quoted_columns}) values ({values})"),
                [dict(row) for row in rows],
            )
            print(f"{table}: {len(rows)} rows migrated")

        sequence_tables = [
            "app_users",
            "import_batches",
            "orders",
            "order_tests",
            "specimen_arrivals",
            "scan_logs",
            "department_routes",
            "routing_rules",
            "culture_rules",
            "micro_culture_assignments",
        ]
        for table in sequence_tables:
            pg_conn.execute(
                text(
                    "select setval(pg_get_serial_sequence(:table_name, 'id'), "
                    "coalesce((select max(id) from " + table + "), 1), true)"
                ),
                {"table_name": table},
            )

    print("Migration complete.")


if __name__ == "__main__":
    main()
