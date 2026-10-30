from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class Pose:
    head_x: float = 0.0
    head_y: float = 0.0
    lean: float = 0.0
    arm_left: float = 0.0
    arm_right: float = 0.0
    leg_left: float = 0.0
    leg_right: float = 0.0
    sit: float = 0.0


POSES = {
    "standing": Pose(),
    "idle": Pose(),
    "walking": Pose(arm_left=-0.08, arm_right=0.08),
    "running": Pose(lean=0.12, arm_left=-0.25, arm_right=0.25),
    "sitting": Pose(head_y=0.02, lean=-0.08, arm_left=0.12, arm_right=-0.12, sit=1.0),
    "thinking": Pose(head_x=-0.04, head_y=-0.02, arm_right=-0.42),
    "looking_up": Pose(head_y=-0.07, lean=-0.03),
    "looking_away": Pose(head_x=0.08, lean=-0.06),
    "sad": Pose(head_y=0.06, lean=-0.14, arm_left=0.2, arm_right=-0.2),
    "happy": Pose(head_y=-0.04, lean=0.03, arm_left=-0.35, arm_right=0.35),
    "confused": Pose(head_x=0.04, head_y=-0.02, lean=0.05, arm_right=-0.38),
    "pointing": Pose(arm_right=-0.9),
    "lonely": Pose(head_y=0.08, lean=-0.12, arm_left=0.16, arm_right=-0.16),
    "curious": Pose(head_y=-0.04, lean=0.1, arm_right=-0.28),
    "determined": Pose(lean=0.11, arm_left=-0.1, arm_right=0.1),
    "tired": Pose(head_y=0.09, lean=-0.18, arm_left=0.12, arm_right=-0.12),
    "hopeful": Pose(head_y=-0.06, lean=0.04, arm_left=-0.25, arm_right=0.25),
    "lost": Pose(head_x=-0.04, head_y=0.08, lean=-0.1),
    "peaceful": Pose(head_y=-0.02, lean=0.0, arm_left=0.12, arm_right=-0.12),
    "excited": Pose(head_y=-0.06, lean=0.05, arm_left=-0.65, arm_right=0.65),
    "contemplative": Pose(head_y=0.025, lean=-0.04, arm_right=-0.35),
}


def pose_at(
    name: str,
    time_seconds: float,
    walking: bool = False,
    emotion: str | None = None,
) -> dict[str, float | bool]:
    pose = POSES.get(name, POSES["standing"])
    emotional_pose = POSES.get(emotion or "", Pose())
    phase = time_seconds * (2 * math.pi) * (1.5 if name == "running" else 0.8)
    stride = math.sin(phase) * (0.32 if walking or name == "running" else 0.0)
    bounce = abs(math.sin(phase * 2)) * (0.012 if walking else 0.0)
    return {
        "head_x": pose.head_x + emotional_pose.head_x * 0.5,
        "head_y": pose.head_y + emotional_pose.head_y * 0.5 - bounce + math.sin(time_seconds * 2.2) * 0.004,
        "lean": pose.lean + emotional_pose.lean * 0.5 + math.sin(time_seconds * 1.1) * 0.003,
        "arm_left": pose.arm_left + emotional_pose.arm_left * 0.5 + stride,
        "arm_right": pose.arm_right + emotional_pose.arm_right * 0.5 - stride,
        "leg_left": pose.leg_left + emotional_pose.leg_left * 0.5 + stride,
        "leg_right": pose.leg_right + emotional_pose.leg_right * 0.5 - stride,
        "sit": pose.sit,
        "stride": stride,
    }
