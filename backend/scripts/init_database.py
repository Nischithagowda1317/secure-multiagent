from __future__ import annotations

import argparse
import json
import re
import sqlite3
from pathlib import Path

import pandas as pd

from _bootstrap import PROJECT_ROOT


TABLE_GROUPS = {
    "identity_access": "core/identity_access",
    "hr": "core/hr",
    "projects": "core/projects",
    "sales_finance": "core/sales_finance",
    "agents": "core/agents",
    "security_audit": "core/security_audit",
    "rag": "core/rag",
    "evaluation": "core/evaluation",
}


def safe_table_name(group: str, stem: str) -> str:
    value = re.sub(r"[^a-zA-Z0-9_]+", "_", f"{group}_{stem}").lower()
    return value.strip("_")


def main(force: bool) -> None:
    dataset = PROJECT_ROOT / "datasets" / "Secure_Multi_Agent_Enterprise_Dataset"
    database = PROJECT_ROOT / "runtime" / "enterprise_data.db"
    if database.exists() and not force:
        print(f"[SKIP] Database already exists: {database}")
        return
    database.unlink(missing_ok=True)
    manifest = []
    with sqlite3.connect(database) as connection:
        for group, relative in TABLE_GROUPS.items():
            folder = dataset / relative
            for csv_path in sorted(folder.glob("*.csv")):
                table = safe_table_name(group, csv_path.stem)
                frame = pd.read_csv(csv_path, encoding="utf-8-sig")
                frame.to_sql(table, connection, index=False, if_exists="replace")
                manifest.append({"table": table, "rows": len(frame), "source": str(csv_path.relative_to(dataset))})
                print(f"Loaded {table}: {len(frame)} rows")
        connection.execute("CREATE INDEX IF NOT EXISTS idx_projects_id ON projects_projects(project_id)")
        connection.execute("CREATE INDEX IF NOT EXISTS idx_tasks_project ON projects_tasks(project_id)")
        connection.execute("CREATE INDEX IF NOT EXISTS idx_employees_id ON hr_employees(employee_id)")
        connection.execute("CREATE INDEX IF NOT EXISTS idx_sales_region ON sales_finance_sales_orders(region)")
    (PROJECT_ROOT / "runtime" / "database_manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )
    print(f"[OK] SQLite demonstration database saved to {database}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    main(args.force)
