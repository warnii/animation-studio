# NeverDotEnds Animation Studio

A local, offline-first animation studio for turning a short story into editable scenes and rendering a procedural stickman reel to MP4. It uses a consistent, featureless silhouette and a built-in library of 15 layered environments. No paid AI service is needed for the story planner, preview, project files, or video rendering.

## Windows setup

1. Install Python 3.11 or newer and make sure `python` is on PATH.
2. Double-click `setup.bat` to create a virtual environment and install dependencies.
3. Double-click `run.bat`. The studio opens in your browser at a local address.

The bundled `imageio-ffmpeg` package supplies FFmpeg when a system FFmpeg is not on PATH. You can also install FFmpeg separately. The application reports an actionable error if neither is available.

## Typical workflow

1. Enter a story and select **Generate scene breakdown**.
2. Review and edit the scene JSON. Each scene includes duration, environment, pose, emotion, movement, camera values, and transition.
3. Preview any scene by its zero-based index.
4. Optionally upload an audio file. It is looped or trimmed to match the reel.
5. Choose the output dimensions and frame rate, then select **Generate Reel / Export MP4**.
6. Save the project JSON to `projects/`; rendered videos go to `renders/`.

The deterministic story planner is a local keyword-based baseline, not an LLM. External AI generation is not implemented or falsely reported as available. Scene plans can always be edited manually.

## Project and CLI

- Example project: `sample_project/project.json`
- Rendered example video: `renders/sample-reel.mp4`
- Render the sample: `python render_sample.py`
- Run tests: `python -m unittest discover -s tests -v`
- Projects are portable JSON files. Use **Open project** and enter a project JSON path to resume editing.

The checked-in sample project is configured for a quick 360 x 640, 12 FPS preview render. The studio defaults to 1080 x 1920 at 30 FPS for new exports.

## Git

Generated project data, virtual environments, credentials, and new renders are excluded by `.gitignore`. The portable sample project and its small demo MP4 are included.

To connect this local repository to a new GitHub repository and push the staged files:

```powershell
git remote add origin https://github.com/<your-account>/<your-repository>.git
git commit -m "Initial NeverDotEnds Animation Studio"
git push -u origin main
```

Review `git status` before committing. Do not add `.env` files or private project assets.

## Current scope

The renderer eases the character between screenplay action beats, animates sitting/standing changes, moves the camera gently, and blends adjacent shots. It is still procedural 2D animation rather than AI-generated footage. Imported audio is mixed as a single looping music track. Advanced skeletal IK editing, multi-track audio editing, and AI image/video generation are not included yet.
