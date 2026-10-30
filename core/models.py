from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any
from uuid import uuid4

ENVIRONMENTS = (
    "rooftop",
    "sunset_hill",
    "bedroom",
    "city_street",
    "empty_road",
    "classroom",
    "library",
    "rainy_window",
    "beach",
    "bridge",
    "forest",
    "stairs",
    "hallway",
    "transport",
    "open_sky",
)

POSES = (
    "standing",
    "idle",
    "walking",
    "running",
    "sitting",
    "thinking",
    "looking_up",
    "looking_away",
    "sad",
    "happy",
    "confused",
    "pointing",
    "lonely",
    "curious",
    "determined",
    "tired",
    "hopeful",
    "lost",
    "peaceful",
    "excited",
    "contemplative",
)

TRANSITIONS = ("cut", "fade", "crossfade", "pan", "zoom")


@dataclass
class Scene:
    scene_id: str = field(default_factory=lambda: uuid4().hex[:8])
    name: str = "New scene"
    description: str = ""
    duration: float = 4.0
    environment: str = "sunset_hill"
    pose: str = "standing"
    emotion: str = "peaceful"
    movement: str = "idle"
    character_x: float = 0.5
    camera_zoom: float = 1.0
    camera_pan: float = 0.0
    transition: str = "fade"
    lighting: str = "cinematic"

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Scene":
        if not isinstance(data, dict):
            raise ValueError("Each scene must be a JSON object.")
        values = {key: data[key] for key in cls.__dataclass_fields__ if key in data}
        scene = cls(**values)
        if not scene.scene_id or not scene.name:
            raise ValueError("Each scene needs a scene_id and name.")
        if not 0.25 <= float(scene.duration) <= 120:
            raise ValueError(f"Scene '{scene.name}' duration must be from 0.25 to 120 seconds.")
        if scene.environment not in ENVIRONMENTS:
            raise ValueError(f"Unknown environment '{scene.environment}'.")
        if scene.pose not in POSES:
            raise ValueError(f"Unknown pose '{scene.pose}'.")
        if scene.transition not in TRANSITIONS:
            raise ValueError(f"Unknown transition '{scene.transition}'.")
        if not 0 <= float(scene.character_x) <= 1:
            raise ValueError(f"Scene '{scene.name}' character_x must be between 0 and 1.")
        if not 0.5 <= float(scene.camera_zoom) <= 2.5:
            raise ValueError(f"Scene '{scene.name}' camera_zoom must be between 0.5 and 2.5.")
        scene.duration = float(scene.duration)
        scene.character_x = float(scene.character_x)
        scene.camera_zoom = float(scene.camera_zoom)
        scene.camera_pan = float(scene.camera_pan)
        return scene


@dataclass
class Project:
    name: str = "Untitled Reel"
    story: str = ""
    scenes: list[Scene] = field(default_factory=list)
    audio_path: str = ""
    width: int = 1080
    height: int = 1920
    fps: int = 30

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["scenes"] = [asdict(scene) for scene in self.scenes]
        data["schema_version"] = 1
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Project":
        if not isinstance(data, dict):
            raise ValueError("Project file must contain a JSON object.")
        scenes = [Scene.from_dict(scene) for scene in data.get("scenes", [])]
        width = int(data.get("width", 1080))
        height = int(data.get("height", 1920))
        fps = int(data.get("fps", 30))
        if (
            not 160 <= width <= 3840
            or not 160 <= height <= 3840
            or width % 2
            or height % 2
            or fps not in (12, 24, 30, 60)
        ):
            raise ValueError("Project resolution or frame rate is invalid.")
        return cls(
            name=str(data.get("name", "Untitled Reel")),
            story=str(data.get("story", "")),
            scenes=scenes,
            audio_path=str(data.get("audio_path", "")),
            width=width,
            height=height,
            fps=fps,
        )
