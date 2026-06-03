# Short Video Generation

This project can now generate simple vertical stickman short videos from a topic.

## Install Video Dependencies

Install the video dependencies into the local ignored dependency folder:

```powershell
python -m pip install --target .video_deps -r requirements-video.txt
```

If the system `python` command is unavailable, use the Codex bundled Python runtime.

## Generate One Silent Video

```powershell
python video_generator.py "总担心别人怎么看我" --seconds 45 --fps 12 --width 720 --height 1280 --out outputs/videos
```

## Generate One Voiced Video

On Windows, the `--voice` option uses SAPI voices. This machine has:

```text
Microsoft Huihui Desktop - Chinese (Simplified)
```

Generate a voiced sample:

```powershell
python video_generator.py "总担心别人怎么看我" --fps 12 --width 720 --height 1280 --out outputs/videos --voice --voice-keyword Chinese --voice-rate 1
```

When voice mode is enabled, the generator creates per-sentence audio clips and aligns subtitle timing to the measured WAV durations.

## Batch Generation

Generate the first two built-in topics as a quick test:

```powershell
python video_generator.py --batch30 --limit 2 --seconds 3 --fps 2 --width 360 --height 640 --out outputs/videos/batch_test
```

Generate all built-in topics:

```powershell
python video_generator.py --batch30 --out outputs/videos
```

Generate from a topic file:

```powershell
python video_generator.py --topic-file topics/anxiety.txt --out outputs/videos
```

## Outputs

Videos are written to `outputs/videos/`, which is ignored by Git to avoid committing large generated files.

## Current MVP Limits

- Visuals are deterministic code-drawn stickman scenes.
- Voice is local Windows SAPI, not studio-grade AI voice.
- Background music and publishing automation are not included yet.
