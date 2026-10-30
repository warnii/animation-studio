from __future__ import annotations

import re

from core.models import Scene

ENVIRONMENT_WORDS = {
    "rooftop": ("rooftop", "roof"),
    "sunset_hill": ("sunset", "hill", "mountain", "horizon"),
    "bedroom": ("bedroom", "bed", "room"),
    "city_street": ("city", "street", "traffic", "sidewalk"),
    "empty_road": ("road", "highway", "crossroads"),
    "classroom": ("classroom", "school", "lesson"),
    "library": ("library", "books", "shelf"),
    "rainy_window": ("rain", "rainy", "window"),
    "beach": ("beach", "ocean", "sea", "shore"),
    "bridge": ("bridge", "overlook"),
    "forest": ("forest", "woods", "tree"),
    "stairs": ("stairs", "staircase", "steps"),
    "hallway": ("hallway", "corridor"),
    "transport": ("bus", "train", "subway", "station"),
    "open_sky": ("stars", "stargazing", "sky", "night sky"),
}

POSE_WORDS = {
    "sitting": ("sit", "sits", "sitting", "seated"),
    "walking": ("walk", "walks", "walking", "wanders", "leaves"),
    "running": ("run", "runs", "running", "sprints"),
    "thinking": ("think", "thinks", "thinking", "remember", "remembers"),
    "looking_up": ("looks up", "look up", "gazes", "watches"),
    "pointing": ("point", "points", "pointing"),
    "standing": ("stand", "stands", "standing", "rises", "gets up"),
}

EMOTION_WORDS = {
    "lonely": ("lonely", "alone", "isolated"),
    "sad": ("sad", "cries", "grief", "heartbroken"),
    "curious": ("curious", "wonders", "explores"),
    "determined": ("determined", "decides", "resolve"),
    "tired": ("tired", "exhausted", "weary"),
    "hopeful": ("hope", "hopeful", "future", "dawn"),
    "excited": ("excited", "joy", "celebrates"),
    "confused": ("confused", "uncertain", "lost"),
    "peaceful": ("peaceful", "calm", "quiet", "rests"),
    "contemplative": ("reflects", "contemplates", "remembers"),
    "happy": ("happy", "smiles", "laughs"),
}


def _match(text: str, table: dict[str, tuple[str, ...]], default: str) -> str:
    lowered = text.lower()
    matches = [
        (match.start(), -len(term), label)
        for label, terms in table.items()
        for term in terms
        if (match := re.search(rf"(?<!\w){re.escape(term)}(?!\w)", lowered))
    ]
    return min(matches)[2] if matches else default


def _action_beats(sentence: str) -> list[str]:
    clauses = re.split(r"\s+(?:and\s+then|then|and)\s+", sentence, flags=re.IGNORECASE)
    if len(clauses) == 1:
        return clauses

    beats: list[str] = []
    pending = clauses[0].strip()
    for clause in clauses[1:]:
        clause = clause.strip()
        has_action = _match(pending, POSE_WORDS, "") != "" and _match(clause, POSE_WORDS, "") != ""
        if has_action:
            beats.append(pending)
            pending = clause
        else:
            pending = f"{pending}, {clause}"
    beats.append(pending)
    return [beat for beat in beats if beat]


def plan_story(story: str) -> list[Scene]:
    """Create editable, deterministic scenes without requiring a paid AI provider."""
    if not story or not story.strip():
        raise ValueError("Enter a story or reel idea before generating scenes.")
    sentences = [part.strip() for part in re.split(r"(?<=[.!?])\s+|\n+", story) if part.strip()]
    parts = [beat for sentence in sentences for beat in _action_beats(sentence)]
    parts = parts[:12]
    scenes: list[Scene] = []
    previous_environment = "sunset_hill"
    for index, description in enumerate(parts):
        environment = _match(description, ENVIRONMENT_WORDS, previous_environment)
        pose = _match(description, POSE_WORDS, "standing")
        emotion = _match(description, EMOTION_WORDS, "contemplative")
        movement = "walk" if pose in ("walking", "running") else ("sit" if pose == "sitting" else "idle")
        duration = min(7.0, max(3.0, 2.5 + len(description.split()) * 0.22))
        name = f"Scene {index + 1}: {description[:38].rstrip(' .,')}"
        scenes.append(
            Scene(
                name=name,
                description=description,
                duration=round(duration, 1),
                environment=environment,
                pose=pose,
                emotion=emotion,
                movement=movement,
                character_x=0.4 if index % 2 == 0 else 0.62,
                transition="fade" if index == 0 else "crossfade",
            )
        )
        previous_environment = environment
    return scenes
