from __future__ import annotations

from config.settings import RENDERS_DIR, SAMPLE_PROJECT
from core.project_manager import load_project
from core.rendering_engine import iter_project_frames
from core.video_exporter import export_mp4


def main() -> None:
    project = load_project(SAMPLE_PROJECT)
    output = RENDERS_DIR / "sample-reel.mp4"
    result = export_mp4(iter_project_frames(project), project, output)
    print(f"Rendered sample video: {result}")


if __name__ == "__main__":
    main()
