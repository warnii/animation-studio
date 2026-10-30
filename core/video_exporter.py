from __future__ import annotations

import shutil
import subprocess
from collections.abc import Iterable
from pathlib import Path
from typing import Callable

from PIL import Image

from core.models import Project


def find_ffmpeg() -> str:
    executable = shutil.which("ffmpeg")
    if executable:
        return executable
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError as error:
        raise RuntimeError(
            "FFmpeg was not found. Install FFmpeg and add it to PATH, or install imageio-ffmpeg "
            "with 'python -m pip install imageio-ffmpeg'."
        ) from error


def export_mp4(
    frames: Iterable[Image.Image],
    project: Project,
    output_path: str | Path,
    cancelled=None,
    progress_callback: Callable[[int, int], None] | None = None,
) -> Path:
    target = Path(output_path).expanduser().resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    ffmpeg = find_ffmpeg()
    width, height = project.width, project.height
    if not 160 <= width <= 3840 or not 160 <= height <= 3840 or width % 2 or height % 2:
        raise ValueError("MP4 dimensions must be even numbers between 160 and 3840 pixels.")
    total_frames = sum(max(1, round(scene.duration * project.fps)) for scene in project.scenes)

    command = [
        ffmpeg,
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-f",
        "rawvideo",
        "-pix_fmt",
        "rgb24",
        "-s:v",
        f"{width}x{height}",
        "-r",
        str(project.fps),
        "-i",
        "pipe:0",
    ]
    audio_path = Path(project.audio_path).expanduser() if project.audio_path else None
    if audio_path:
        if not audio_path.is_file():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")
        command.extend(["-stream_loop", "-1", "-i", str(audio_path), "-map", "0:v:0", "-map", "1:a:0"])
    command.extend(
        [
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            "21",
            "-pix_fmt",
            "yuv420p",
        ]
    )
    if audio_path:
        command.extend(["-c:a", "aac", "-b:a", "192k", "-shortest"])
    else:
        command.append("-an")
    command.extend(["-movflags", "+faststart", str(target)])

    process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    assert process.stdin is not None
    frames_written = 0
    try:
        for frame in frames:
            if cancelled is not None and cancelled.is_set():
                process.terminate()
                raise InterruptedError("Rendering cancelled.")
            if frame.size != (width, height):
                frame = frame.resize((width, height), Image.Resampling.LANCZOS)
            process.stdin.write(frame.convert("RGB").tobytes())
            frames_written += 1
            if progress_callback is not None and (
                frames_written % max(1, project.fps) == 0 or frames_written == total_frames
            ):
                progress_callback(frames_written, total_frames)
        process.stdin.close()
        stderr = process.stderr.read() if process.stderr else b""
        return_code = process.wait()
        if return_code != 0:
            raise RuntimeError(f"FFmpeg failed with exit code {return_code}: {stderr.decode(errors='replace')[-2000:]}")
        if not target.is_file() or target.stat().st_size == 0:
            raise RuntimeError("FFmpeg completed but did not produce an MP4 file.")
        validation = subprocess.run(
            [ffmpeg, "-hide_banner", "-loglevel", "error", "-i", str(target), "-f", "null", "-"],
            capture_output=True,
            text=True,
            check=False,
        )
        if validation.returncode != 0:
            raise RuntimeError(f"Exported MP4 failed decode validation: {validation.stderr[-2000:]}")
        return target
    except BaseException:
        if process.poll() is None:
            process.terminate()
            process.wait(timeout=10)
        raise
    finally:
        if process.stdin is not None and not process.stdin.closed:
            process.stdin.close()
        if process.stderr is not None:
            process.stderr.close()
