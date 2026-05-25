from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from security_agent.database import init_database


def main() -> None:
    database = init_database()
    print(f"Initialized SQLite database: {database.db_path}")


if __name__ == "__main__":
    main()

