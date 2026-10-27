"""The Docker entrypoint runs `alembic upgrade head`; make sure that works from a clean DB."""

import os
import sqlite3
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_alembic_upgrade_head_builds_schema(tmp_path):
    db = tmp_path / "migrated.db"
    env = {**os.environ, "DATABASE_URL": f"sqlite:///{db}"}
    result = subprocess.run(
        # Use the console script exactly like scripts/docker-entrypoint.sh does;
        # `python -m alembic` would hide a missing prepend_sys_path setting.
        [str(Path(sys.executable).parent / "alembic"), "upgrade", "head"],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    tables = {row[0] for row in sqlite3.connect(db).execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert "alembic_version" in tables
    assert len(tables) > 1
