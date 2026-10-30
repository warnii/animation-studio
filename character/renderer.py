from __future__ import annotations

import math

from PIL import Image, ImageDraw


def _limb(draw: ImageDraw.ImageDraw, start: tuple[float, float], end: tuple[float, float], width: int) -> None:
    draw.line((start, end), fill=(5, 6, 11), width=width)
    radius = max(2, width // 2)
    for point in (start, end):
        x, y = point
        draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=(5, 6, 11))


def draw_character(
    image: Image.Image,
    x_fraction: float,
    baseline_fraction: float,
    scale: float,
    pose: dict[str, float | bool],
    facing: str = "front",
) -> None:
    """Draw the same featureless, proportion-locked silhouette for every scene."""
    width, height = image.size
    unit = height / 1000 * scale
    cx = width * x_fraction
    baseline = height * baseline_fraction
    flip = -1 if facing == "left" else 1
    tilt = float(pose["lean"])
    stride = float(pose["stride"])
    sitting = max(0.0, min(1.0, float(pose["sit"])))

    # A soft ground shadow anchors the character in the environment.
    shadow = Image.new("RGBA", image.size, (0, 0, 0, 0))
    shadow_draw = ImageDraw.Draw(shadow)
    shadow_w = 55 * unit
    shadow_draw.ellipse((cx - shadow_w, baseline - 5 * unit, cx + shadow_w, baseline + 8 * unit), fill=(0, 0, 0, 100))
    image.alpha_composite(shadow)
    draw = ImageDraw.Draw(image)

    head_r = 40 * unit
    head_x = cx + float(pose["head_x"]) * height * flip
    head_y = baseline - (280 - float(pose["head_y"]) * 300) * unit
    shoulder_y = baseline - (212 - 22 * sitting) * unit
    hip_y = baseline - (100 + 20 * sitting) * unit
    body_x = cx + tilt * 90 * unit * flip
    thickness = max(3, round(18 * unit))

    # Torso taper keeps the joints joined while preserving the original simple design.
    draw.polygon(
        [
            (body_x - 25 * unit, shoulder_y),
            (body_x + 25 * unit, shoulder_y),
            (cx + 24 * unit, hip_y),
            (cx - 24 * unit, hip_y),
        ],
        fill=(5, 6, 11),
    )
    neck = (body_x, shoulder_y - 4 * unit)
    draw.ellipse((neck[0] - 12 * unit, neck[1] - 8 * unit, neck[0] + 12 * unit, neck[1] + 16 * unit), fill=(5, 6, 11))

    left_shoulder = (body_x - 25 * unit, shoulder_y + 5 * unit)
    right_shoulder = (body_x + 25 * unit, shoulder_y + 5 * unit)
    left_hip = (cx - 18 * unit, hip_y)
    right_hip = (cx + 18 * unit, hip_y)
    left_arm_angle = float(pose["arm_left"]) + stride
    right_arm_angle = float(pose["arm_right"]) - stride
    arm_len = 105 * unit

    for shoulder, angle, side in ((left_shoulder, left_arm_angle, -1), (right_shoulder, right_arm_angle, 1)):
        angle *= flip
        elbow = (
            shoulder[0] + side * math.sin(angle) * arm_len * 0.52,
            shoulder[1] + math.cos(angle) * arm_len * 0.52,
        )
        hand = (
            shoulder[0] + side * math.sin(angle) * arm_len,
            shoulder[1] + math.cos(angle) * arm_len,
        )
        if abs(angle) > 0.65:
            hand = (shoulder[0] + side * arm_len * 0.8, shoulder[1] - arm_len * 0.45)
            elbow = (shoulder[0] + side * arm_len * 0.43, shoulder[1] - arm_len * 0.12)
        _limb(draw, shoulder, elbow, thickness)
        _limb(draw, elbow, hand, max(3, round(thickness * 0.82)))
        draw.ellipse((hand[0] - thickness * 0.58, hand[1] - thickness * 0.58, hand[0] + thickness * 0.58, hand[1] + thickness * 0.58), fill=(5, 6, 11))

    legs = (float(pose["leg_left"]) + stride, float(pose["leg_right"]) - stride)
    hips = [left_hip, right_hip]
    knees = []
    ankles = []
    for side, angle in zip((-1, 1), legs):
        standing_knee = (
            cx + side * 32 * unit + math.sin(angle) * 47 * unit,
            baseline - (52 + abs(math.sin(angle)) * 20) * unit,
        )
        standing_ankle = (cx + side * 30 * unit + math.sin(angle) * 90 * unit, baseline - 5 * unit)
        sitting_knee = (cx + side * 72 * unit, hip_y + 4 * unit)
        sitting_ankle = (
            cx + (-74 if side < 0 else 84) * unit,
            baseline - 5 * unit,
        )
        knee = tuple(a * (1 - sitting) + b * sitting for a, b in zip(standing_knee, sitting_knee))
        ankle = tuple(a * (1 - sitting) + b * sitting for a, b in zip(standing_ankle, sitting_ankle))
        knees.append(knee)
        ankles.append(ankle)

    for hip, knee, ankle, side in zip(hips, knees, ankles, (-1, 1)):
        _limb(draw, hip, knee, thickness)
        _limb(draw, knee, ankle, max(3, round(thickness * 0.88)))
        foot_x = ankle[0] + side * 12 * unit
        draw.ellipse((foot_x - 13 * unit, ankle[1] - 7 * unit, foot_x + 13 * unit, ankle[1] + 7 * unit), fill=(5, 6, 11))

    draw.ellipse((head_x - head_r, head_y - head_r, head_x + head_r, head_y + head_r), fill=(5, 6, 11))
