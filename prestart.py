"""
Runs before the app starts on Render.
Clears stale migration state and applies the latest schema.
"""
import subprocess
import sys
from sqlalchemy import create_engine, text
import os


def run(cmd: str) -> int:
    print(f">> {cmd}")
    result = subprocess.run(cmd, shell=True)
    return result.returncode


def clear_migration_version():
    """Wipe the alembic_version table so upgrade head can run cleanly."""
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        print("No DATABASE_URL found — skipping version clear.")
        return
    try:
        engine = create_engine(db_url)
        with engine.connect() as conn:
            conn.execute(text("DELETE FROM alembic_version"))
            conn.commit()
        print("Cleared alembic_version table.")
    except Exception as e:
        # Table may not exist yet on a brand new DB — that's fine
        print(f"Could not clear alembic_version (may not exist yet): {e}")


def main():
    # 1. Clear any stale revision hash from the DB
    clear_migration_version()

    # 2. Apply all migrations from scratch
    rc = run("alembic upgrade head")
    if rc != 0:
        print("Migration failed. Exiting.")
        sys.exit(1)

    print("Migrations applied successfully.")


if __name__ == "__main__":
    main()
