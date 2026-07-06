"""
Run this once to reset the Render database and sync Alembic.
Usage: python fix_render_db.py
"""
import subprocess
from sqlalchemy import create_engine, text
from app.database import Base
import app.models  # noqa — registers all models

DB_URL = input("Paste your Render External Database URL: ").strip()

engine = create_engine(DB_URL)

print("\n1. Dropping all existing tables...")
Base.metadata.drop_all(bind=engine)
print("   Done.")

print("\n2. Creating all tables from current models...")
Base.metadata.create_all(bind=engine)
print("   Done.")

print("\n3. Getting current Alembic revision...")
result = subprocess.run("alembic heads", shell=True, capture_output=True, text=True)
revision = result.stdout.strip().split()[0]
print(f"   Revision: {revision}")

print("\n4. Stamping revision into DB...")
with engine.connect() as conn:
    conn.execute(text("DELETE FROM alembic_version"))
    conn.execute(text("INSERT INTO alembic_version (version_num) VALUES (:rev)"), {"rev": revision})
    conn.commit()
print("   Done.")

print("\nAll done! Render DB is reset and in sync with Alembic.")
print("Now push to GitHub and trigger a manual redeploy on Render.")
