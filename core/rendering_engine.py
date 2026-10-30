from __future__ import annotations

from collections.abc import Iterator

from PIL import Image

from animation.interpolation import lerp, smoothstep
from character.pose_library import pose_at
from character.renderer import draw_character
from core.models import Project, Scene
from environments.renderer import render_environment

POSE_FIELDS = ("head_x", "head_y", "lean", "arm_left", "arm_right", "leg_left", "leg_right", "sit", "stride")


def _scene_pose(scene: Scene, elapsed: float) -> dict[str, float | bool]:
    return pose_at(
        scene.pose,
        elapsed,
        walking=scene.movement in ("walk", "run"),
        emotion=scene.emotion,
    )


def _blend_pose(
    start: dict[str, float | bool],
    end: dict[str, float | bool],
    amount: float,
) -> dict[str, float | bool]:
    eased = smoothstep(amount)
    return {
        field: lerp(float(start[field]), float(end[field]), eased)
        for field in POSE_FIELDS
    }


def _walk_end_x(scene: Scene) -> float:
    distance = 0.14 if scene.movement == "walk" else 0.23 if scene.movement == "run" else 0
    return max(0.12, min(0.88, scene.character_x + distance / 2))


def _scene_frame(
    scene: Scene,
    elapsed: float,
    size: tuple[int, int],
    fps: int,
    frame_index: int,
    previous_scene: Scene | None = None,
    outgoing_frame: Image.Image | None = None,
) -> Image.Image:
    width, height = size
    duration = max(scene.duration, 0.001)
    progress = min(1.0, max(0.0, elapsed / duration))
    background = render_environment(scene.environment, width, height).copy()

    # Ease the camera through each shot instead of jumping to its final framing.
    camera_target = scene.camera_zoom if scene.camera_zoom != 1 else 1.035
    zoom = lerp(1.0, camera_target, progress)
    pan = scene.camera_pan * smoothstep(progress)
    if zoom != 1.0 or pan:
        crop_width, crop_height = int(width / zoom), int(height / zoom)
        left = int((width - crop_width) / 2 + pan * width * 0.25)
        top = int((height - crop_height) / 2)
        left = max(0, min(width - crop_width, left))
        top = max(0, min(height - crop_height, top))
        background = background.crop((left, top, left + crop_width, top + crop_height)).resize(
            (width, height), Image.Resampling.LANCZOS
        )

    target_pose = _scene_pose(scene, elapsed)
    if previous_scene is None:
        source_pose = pose_at("standing", 0)
        source_x = scene.character_x
    else:
        source_pose = _scene_pose(previous_scene, previous_scene.duration)
        source_x = _walk_end_x(previous_scene)

    movement_seconds = min(1.0, duration * 0.4)
    movement_progress = smoothstep(elapsed / movement_seconds) if movement_seconds else 1.0
    pose = _blend_pose(source_pose, target_pose, movement_progress)
    target_x = _walk_end_x(scene)
    character_x = lerp(source_x, target_x, progress)
    draw_character(background, max(0.12, min(0.88, character_x)), 0.79, 1.0, pose)

    transition_seconds = min(0.65, duration * 0.3)
    if outgoing_frame is not None and scene.transition == "crossfade" and transition_seconds:
        alpha = smoothstep(elapsed / transition_seconds)
        background = Image.blend(outgoing_frame.convert("RGBA"), background, alpha)
    elif previous_scene is None and scene.transition == "fade" and transition_seconds:
        alpha = smoothstep(elapsed / transition_seconds)
        background = Image.blend(Image.new("RGBA", size, (0, 0, 0, 255)), background, alpha)
    elif previous_scene is not None and scene.transition == "fade" and transition_seconds:
        alpha = smoothstep(elapsed / transition_seconds)
        background = Image.blend(Image.new("RGBA", size, (0, 0, 0, 255)), background, alpha)

    return background.convert("RGB")


def iter_project_frames(
    project: Project,
    size: tuple[int, int] | None = None,
    fps: int | None = None,
    cancelled=None,
) -> Iterator[Image.Image]:
    if not project.scenes:
        raise ValueError("This project has no scenes. Generate or add scenes before rendering.")
    render_size = size or (project.width, project.height)
    frame_rate = fps or project.fps
    previous_scene = None
    outgoing_frame = None
    for scene in project.scenes:
        if cancelled is not None and cancelled.is_set():
            return
        frame_count = max(1, round(scene.duration * frame_rate))
        for frame_index in range(frame_count):
            if cancelled is not None and cancelled.is_set():
                return
            yield _scene_frame(
                scene,
                frame_index / frame_rate,
                render_size,
                frame_rate,
                frame_index,
                previous_scene=previous_scene,
                outgoing_frame=outgoing_frame,
            )
        previous_scene = scene
        outgoing_frame = _scene_frame(
            scene,
            scene.duration,
            render_size,
            frame_rate,
            frame_count,
            previous_scene=previous_scene,
        )


def render_preview(project: Project, scene_index: int = 0, width: int = 360, height: int = 640) -> Image.Image:
    if not project.scenes:
        raise ValueError("There are no scenes to preview.")
    if scene_index < 0 or scene_index >= len(project.scenes):
        raise ValueError(f"Scene index must be between 0 and {len(project.scenes) - 1}.")
    scene = project.scenes[scene_index]
    previous_scene = project.scenes[scene_index - 1] if scene_index > 0 else None
    outgoing_frame = None
    if previous_scene is not None and scene.transition == "crossfade":
        outgoing_frame = _scene_frame(
            previous_scene,
            previous_scene.duration,
            (width, height),
            project.fps,
            0,
            previous_scene=project.scenes[scene_index - 2] if scene_index > 1 else None,
        )
    return _scene_frame(
        scene,
        min(0.8, scene.duration * 0.4),
        (width, height),
        project.fps,
        0,
        previous_scene=previous_scene,
        outgoing_frame=outgoing_frame,
    )
