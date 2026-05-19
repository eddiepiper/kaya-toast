from __future__ import annotations

import fcntl
import json
import os
import shutil
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator


@contextmanager
def file_lock(path: str | Path) -> Iterator[None]:
    lock_path = Path(path)
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a", encoding="utf-8") as lock_file:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)


def atomic_json_write(data: Any, path: str | Path, backup_path: str | Path | None = None) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    backup = Path(backup_path) if backup_path is not None else None
    if backup is not None and target.exists():
        backup.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(target, backup)

    temp_path = target.with_name(f".{target.name}.tmp")
    temp_path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temp_path, target)


def load_json_with_backup(path: str | Path, default: Any, backup_path: str | Path | None = None) -> Any:
    target = Path(path)
    if not target.exists():
        atomic_json_write(default, target, backup_path=None)
        return default
    try:
        return json.loads(target.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        backup = Path(backup_path) if backup_path is not None else None
        if backup is not None and backup.exists():
            recovered = json.loads(backup.read_text(encoding="utf-8"))
            atomic_json_write(recovered, target, backup_path=None)
            return recovered
        raise
