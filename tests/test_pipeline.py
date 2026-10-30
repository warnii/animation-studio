from __future__ import annotations

import array
import json
import math
import subprocess
import tempfile
import unittest
import wave
from pathlib import Path

from core.models import ENVIRONMENTS, Project, Scene
from core.project_manager import load_project, save_project
from core.rendering_engine import iter_project_frames, render_preview
from core.story_parser import plan_story
from core.video_exporter import export_mp4, find_ffmpeg
from character.pose_library import pose_at
from environments.renderer import render_environment


class StoryPlannerTests(unittest.TestCase):
    def test_story_becomes_editable_scenes(self):
        scenes = plan_story("A lonely stickman sits on a sunset hill. He walks toward the city.")
        self.assertEqual(len(scenes), 2)
        self.assertEqual(scenes[0].environment, "sunset_hill")
        self.assertEqual(scenes[0].pose, "sitting")
        self.assertEqual(scenes[1].environment, "city_street")
        self.assertEqual(scenes[1].movement, "walk")

    def test_compound_action_is_split_into_screenplay_beats(self):
        scenes = plan_story(
            "A lonely stickman sits on a sunset hill. He stands and walks down the empty road toward the city lights."
        )
        self.assertEqual([scene.pose for scene in scenes], ["sitting", "standing", "walking"])
        self.assertEqual(scenes[1].environment, "sunset_hill")
        self.assertEqual(scenes[2].environment, "empty_road")

    def test_empty_story_is_rejected(self):
        with self.assertRaises(ValueError):
            plan_story("  ")


class RenderingTests(unittest.TestCase):
    def test_all_environments_render_images(self):
        for environment in ENVIRONMENTS:
            with self.subTest(environment=environment):
                image = render_environment(environment, 180, 320)
                self.assertEqual(image.size, (180, 320))
                self.assertEqual(image.mode, "RGBA")

    def test_scene_preview_and_frame_sequence(self):
        project = Project(
            scenes=[Scene(duration=0.25, environment="sunset_hill", pose="walking", movement="walk")],
            width=160,
            height=240,
            fps=12,
        )
        self.assertEqual(render_preview(project, width=160, height=240).size, (160, 240))
        self.assertEqual(len(list(iter_project_frames(project))), 3)

    def test_sitting_pose_animates_into_position(self):
        project = Project(
            scenes=[Scene(duration=1, pose="sitting", emotion="lonely")],
            width=160,
            height=240,
            fps=12,
        )
        frames = list(iter_project_frames(project))
        self.assertNotEqual(frames[0].tobytes(), frames[-1].tobytes())

    def test_scene_crossfade_starts_from_previous_shot(self):
        project = Project(
            scenes=[
                Scene(duration=0.25, environment="sunset_hill", transition="fade"),
                Scene(duration=0.25, environment="city_street", transition="crossfade"),
            ],
            width=160,
            height=240,
            fps=12,
        )
        frames = list(iter_project_frames(project))
        self.assertEqual(len(frames), 6)
        self.assertLess(
            sum(abs(a - b) for a, b in zip(frames[2].tobytes(), frames[3].tobytes())),
            160 * 240 * 3 * 20,
        )

    def test_scene_validation_rejects_bad_environment(self):
        with self.assertRaises(ValueError):
            Scene.from_dict({"environment": "not-a-place"})

    def test_emotion_changes_body_language(self):
        neutral = pose_at("standing", 0)
        lonely = pose_at("standing", 0, emotion="lonely")
        self.assertNotEqual(neutral["lean"], lonely["lean"])

    def test_mp4_export_has_expected_video_stream(self):
        project = Project(
            scenes=[Scene(duration=0.25, environment="sunset_hill", pose="walking", movement="walk")],
            width=160,
            height=240,
            fps=12,
        )
        with tempfile.TemporaryDirectory() as temporary:
            output = export_mp4(iter_project_frames(project), project, Path(temporary) / "test.mp4")
            self.assertTrue(output.is_file())
            self.assertGreater(output.stat().st_size, 1000)
            probe = subprocess.run(
                [find_ffmpeg(), "-hide_banner", "-i", str(output)],
                capture_output=True,
                text=True,
                check=False,
            )
        self.assertIn("Video: h264", probe.stderr)
        self.assertIn("160x240", probe.stderr)

    def test_mp4_export_mixes_audio(self):
        project = Project(
            scenes=[Scene(duration=0.25, environment="sunset_hill")],
            width=160,
            height=240,
            fps=12,
        )
        with tempfile.TemporaryDirectory() as temporary:
            audio_path = Path(temporary) / "tone.wav"
            samples = array.array(
                "h",
                (int(4000 * math.sin(2 * math.pi * 440 * sample / 44100)) for sample in range(11025)),
            )
            with wave.open(str(audio_path), "wb") as audio_file:
                audio_file.setnchannels(1)
                audio_file.setsampwidth(2)
                audio_file.setframerate(44100)
                audio_file.writeframes(samples.tobytes())
            project.audio_path = str(audio_path)
            output = export_mp4(iter_project_frames(project), project, Path(temporary) / "with-audio.mp4")
            probe = subprocess.run(
                [find_ffmpeg(), "-hide_banner", "-i", str(output)],
                capture_output=True,
                text=True,
                check=False,
            )
        self.assertIn("Audio: aac", probe.stderr)


class ProjectTests(unittest.TestCase):
    def test_project_round_trip(self):
        project = Project(name="A Small Reel", story="A quiet story.", scenes=[Scene(name="First")])
        with tempfile.TemporaryDirectory() as temporary:
            saved = save_project(project, Path(temporary))
            loaded = load_project(saved)
        self.assertEqual(loaded.name, project.name)
        self.assertEqual(loaded.story, project.story)
        self.assertEqual(loaded.scenes[0].name, "First")

    def test_project_keeps_audio_inside_project_folder(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "music.wav"
            source.write_bytes(b"audio")
            project = Project(name="Audio Reel", scenes=[Scene()], audio_path=str(source))
            saved = save_project(project, root / "projects")
            data = json.loads(saved.read_text(encoding="utf-8"))
            loaded = load_project(saved)
            self.assertEqual(data["audio_path"], "assets/audio/music.wav")
            self.assertEqual(Path(loaded.audio_path).read_bytes(), b"audio")

    def test_project_json_is_valid(self):
        data = Project(scenes=[Scene()]).to_dict()
        self.assertIsInstance(json.loads(json.dumps(data))["scenes"], list)

    def test_project_rejects_out_of_range_resolution(self):
        with self.assertRaises(ValueError):
            Project.from_dict({"width": 8192, "height": 1920, "fps": 30})


if __name__ == "__main__":
    unittest.main()
