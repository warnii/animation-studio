from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

from core.models import Project


def project_directory(name: str, root: Path) -> Path:
    slug = re.sub(r"[^a-zA-Z0-9_-]+", "-", name.strip()).strip("-").lower() or "untitled-project"
    return root / slug


def save_project(project: Project, root: Path) -> Path:
    directory = project_directory(project.name, root)
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / "project.json"
    saved_project = Project.from_dict(project.to_dict())
    if project.audio_path:
        source = Path(project.audio_path).expanduser()
        if not source.is_absolute():
            source = directory / source
        if not source.is_file():
            raise FileNotFoundError(f"Project audio file not found: {source}")
        audio_directory = directory / "assets" / "audio"
        audio_directory.mkdir(parents=True, exist_ok=True)
        audio_copy = audio_directory / source.name
        if source.resolve() != audio_copy.resolve():
            shutil.copy2(source, audio_copy)
        saved_project.audio_path = (Path("assets") / "audio" / source.name).as_posix()
    temporary = target.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(saved_project.to_dict(), indent=2), encoding="utf-8")
    temporary.replace(target)
    return target


def load_project(path: str | Path) -> Project:
    source = Path(path).expanduser()
    if source.is_dir():
        source = source / "project.json"
    if not source.is_file():
        raise FileNotFoundError(f"Project file not found: {source}")
    try:
        data = json.loads(source.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError(f"Invalid project JSON at {source}: {error}") from error
    project = Project.from_dict(data)
    if project.audio_path:
        audio_path = Path(project.audio_path).expanduser()
        if not audio_path.is_absolute():
            audio_path = source.parent / audio_path
        project.audio_path = str(audio_path.resolve())
    return project
