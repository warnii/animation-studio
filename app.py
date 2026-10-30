from __future__ import annotations

import json
import re
import threading

import gradio as gr

from config.settings import (
    APP_NAME,
    DEFAULT_FPS,
    PREVIEW_HEIGHT,
    PREVIEW_WIDTH,
    PROJECTS_DIR,
    RENDERS_DIR,
)
from core.models import Project, Scene
from core.project_manager import load_project, save_project
from core.rendering_engine import iter_project_frames, render_preview
from core.story_parser import plan_story
from core.video_exporter import export_mp4

CANCEL_RENDER = threading.Event()


def _read_scenes(raw: str) -> list[Scene]:
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as error:
        raise ValueError(f"Scene JSON is invalid: {error}") from error
    if not isinstance(data, list):
        raise ValueError("Scenes must be a JSON array.")
    return [Scene.from_dict(item) for item in data]


def _make_project(name: str, story: str, scenes: str, audio: str | None, resolution: str, fps: int) -> Project:
    match = re.fullmatch(r"\s*(\d{2,5})\s*[xX×]\s*(\d{2,5})\s*", resolution or "")
    if not match:
        raise ValueError("Resolution must use width x height, for example 1080x1920.")
    width, height = (int(value) for value in match.groups())
    if not 160 <= width <= 3840 or not 160 <= height <= 3840 or width % 2 or height % 2:
        raise ValueError("Video dimensions must be even and between 160 and 3840 pixels.")
    return Project(
        name=(name or "Untitled Reel").strip(),
        story=story or "",
        scenes=_read_scenes(scenes),
        audio_path=audio or "",
        width=width,
        height=height,
        fps=int(fps),
    )


def generate_scenes(story: str) -> tuple[str, str]:
    try:
        scenes = plan_story(story)
        payload = json.dumps([scene.__dict__ for scene in scenes], indent=2)
        return payload, f"Planned {len(scenes)} scenes. Review or edit the scene JSON before rendering."
    except Exception as error:
        return "[]", f"Could not plan story: {error}"


def preview_scene(
    name: str,
    story: str,
    scenes: str,
    audio: str | None,
    resolution: str,
    fps: int,
    index: float,
):
    try:
        project = _make_project(name, story, scenes, audio, resolution, fps)
        image = render_preview(project, int(index), PREVIEW_WIDTH, PREVIEW_HEIGHT)
        return image, f"Previewing scene {int(index) + 1} of {len(project.scenes)}."
    except Exception as error:
        return None, f"Preview failed: {error}"


def save_current_project(name: str, story: str, scenes: str, audio: str | None, resolution: str, fps: int):
    try:
        project = _make_project(name, story, scenes, audio, resolution, fps)
        path = save_project(project, PROJECTS_DIR)
        return f"Project saved to {path}"
    except Exception as error:
        return f"Save failed: {error}"


def load_saved_project(path: str):
    try:
        project = load_project(path)
        scenes = json.dumps([scene.__dict__ for scene in project.scenes], indent=2)
        return (
            project.name,
            project.story,
            scenes,
            project.audio_path or None,
            f"{project.width}x{project.height}",
            project.fps,
            f"Loaded {len(project.scenes)} scenes from {path}.",
        )
    except Exception as error:
        return "", "", "[]", None, "1080x1920", DEFAULT_FPS, f"Open failed: {error}"


def render_reel(
    name: str,
    story: str,
    scenes: str,
    audio: str | None,
    resolution: str,
    fps: int,
    progress=gr.Progress(track_tqdm=False),
):
    try:
        project = _make_project(name, story, scenes, audio, resolution, fps)
        if not project.scenes:
            raise ValueError("Generate or add at least one scene before rendering.")
        CANCEL_RENDER.clear()
        target = RENDERS_DIR / f"{save_project(project, PROJECTS_DIR).parent.name}.mp4"
        progress(0, desc="Preparing render")

        def update_progress(done: int, total: int) -> None:
            progress(done / total, desc=f"Rendering frames: {done}/{total}")

        result = export_mp4(
            iter_project_frames(project, cancelled=CANCEL_RENDER),
            project,
            target,
            cancelled=CANCEL_RENDER,
            progress_callback=update_progress,
        )
        return str(result), f"Export complete: {result}"
    except InterruptedError:
        return None, "Render cancelled. The project is unchanged."
    except Exception as error:
        return None, f"Render failed: {error}"


def cancel_render():
    CANCEL_RENDER.set()
    return "Cancellation requested."


with gr.Blocks(title=APP_NAME) as demo:
    gr.Markdown(
        "# NeverDotEnds Animation Studio\n"
        "Turn a story into editable scenes, preview a consistent procedural stickman, and render a local MP4. "
        "The built-in story planner works offline; no AI provider or API key is required."
    )
    with gr.Row():
        with gr.Column(scale=3):
            project_name = gr.Textbox(label="Project name", value="Sunset Story")
            story = gr.Textbox(
                label="Story or reel idea",
                lines=5,
                placeholder="A lonely stickman sits on a hill watching the sunset. He stands and walks toward the city lights.",
            )
            plan_button = gr.Button("Generate scene breakdown", variant="primary")
        with gr.Column(scale=2):
            gr.Markdown("### Local project\nProjects are saved as editable JSON under `projects/`.")
            project_path = gr.Textbox(label="Project file to open", placeholder="projects/sunset-story/project.json")
            with gr.Row():
                save_button = gr.Button("Save project")
                open_button = gr.Button("Open project")
    scenes_json = gr.Code(label="Editable scene data (JSON)", language="json", lines=20, value="[]")
    status = gr.Markdown("Enter a story and generate scenes to begin.")

    with gr.Row():
        audio = gr.Audio(label="Optional background music", sources=["upload"], type="filepath")
        with gr.Column():
            resolution = gr.Textbox(label="Output size (width x height)", value="1080x1920")
            fps = gr.Dropdown(label="Frame rate", choices=[12, 24, 30, 60], value=DEFAULT_FPS)
    with gr.Row():
        scene_index = gr.Number(label="Preview scene (starting at 0)", value=0, precision=0)
        preview_button = gr.Button("Preview scene")
        render_button = gr.Button("Generate Reel / Export MP4", variant="primary")
        cancel_button = gr.Button("Cancel render")
    with gr.Row():
        preview = gr.Image(label="Scene preview", height=520)
        rendered_video = gr.Video(label="Rendered MP4")

    project_inputs = [project_name, story, scenes_json, audio, resolution, fps]
    plan_button.click(generate_scenes, inputs=[story], outputs=[scenes_json, status])
    save_button.click(save_current_project, inputs=project_inputs, outputs=[status])
    open_button.click(
        load_saved_project,
        inputs=[project_path],
        outputs=[project_name, story, scenes_json, audio, resolution, fps, status],
    )
    preview_button.click(
        preview_scene,
        inputs=[*project_inputs, scene_index],
        outputs=[preview, status],
    )
    render_button.click(
        render_reel,
        inputs=project_inputs,
        outputs=[rendered_video, status],
    )
    cancel_button.click(cancel_render, outputs=[status])


if __name__ == "__main__":
    PROJECTS_DIR.mkdir(parents=True, exist_ok=True)
    RENDERS_DIR.mkdir(parents=True, exist_ok=True)
    demo.launch(
        inbrowser=True,
        theme=gr.themes.Soft(primary_hue="orange", secondary_hue="slate"),
        css="""
        .gradio-container { max-width: 1280px !important; }
        footer { display: none !important; }
        """,
    )
