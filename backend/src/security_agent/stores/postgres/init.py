from pathlib import Path

import psycopg

from security_agent.stores.postgres.schema import load_schema_sql


def write_schema_file(path: str | Path) -> Path:
    target = Path(path)
    target.write_text(load_schema_sql(), encoding="utf-8")
    return target


def apply_schema(database_url: str) -> None:
    with psycopg.connect(database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute(load_schema_sql())
        connection.commit()

