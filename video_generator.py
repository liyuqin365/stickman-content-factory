from __future__ import annotations

import argparse
import hashlib
import math
import re
import subprocess
import sys
import tempfile
import wave
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
LOCAL_DEPS = PROJECT_ROOT / ".video_deps"
if LOCAL_DEPS.exists():
    sys.path.insert(0, str(LOCAL_DEPS))

try:
    import imageio.v2 as imageio
    import imageio_ffmpeg
    import numpy as np
    from PIL import Image, ImageDraw, ImageFont
except ModuleNotFoundError as exc:
    raise SystemExit(
        "Missing video dependencies. Install them with:\n"
        "python -m pip install --target .video_deps imageio imageio-ffmpeg"
    ) from exc

from content_factory import DEFAULT_TOPICS, generate_script, generate_titles, read_topics_file, sanitize_filename


@dataclass(frozen=True)
class VideoSegment:
    shot: int
    label: str
    voiceover: str
    duration: float


@dataclass(frozen=True)
class CaptionCue:
    shot: int
    label: str
    text: str
    duration: float


@dataclass(frozen=True)
class Fonts:
    title: ImageFont.FreeTypeFont
    subtitle: ImageFont.FreeTypeFont
    label: ImageFont.FreeTypeFont
    small: ImageFont.FreeTypeFont


def load_font(size: int) -> ImageFont.FreeTypeFont:
    candidates = [
        Path("C:/Windows/Fonts/msyh.ttc"),
        Path("C:/Windows/Fonts/msyhbd.ttc"),
        Path("C:/Windows/Fonts/simhei.ttf"),
        Path("C:/Windows/Fonts/simsun.ttc"),
    ]
    for path in candidates:
        if path.exists():
            return ImageFont.truetype(str(path), size=size)
    return ImageFont.load_default(size=size)


def build_fonts(width: int) -> Fonts:
    scale = width / 720
    return Fonts(
        title=load_font(max(28, int(36 * scale))),
        subtitle=load_font(max(26, int(34 * scale))),
        label=load_font(max(20, int(26 * scale))),
        small=load_font(max(16, int(20 * scale))),
    )


def text_width(font: ImageFont.ImageFont, text: str) -> int:
    left, _, right, _ = font.getbbox(text)
    return right - left


def wrap_text(text: str, font: ImageFont.ImageFont, max_width: int) -> list[str]:
    text = re.sub(r"\s+", " ", text.strip())
    lines: list[str] = []
    current = ""

    for char in text:
        candidate = current + char
        if current and text_width(font, candidate) > max_width:
            lines.append(current)
            current = char
        else:
            current = candidate

    if current:
        lines.append(current)
    return lines


def split_voiceover(text: str) -> list[str]:
    parts = [part.strip() for part in re.split(r"(?<=[。！？；])", text) if part.strip()]
    if len(parts) >= 2:
        return parts

    chunks: list[str] = []
    current = ""
    for char in text:
        current += char
        if len(current) >= 24:
            chunks.append(current)
            current = ""
    if current:
        chunks.append(current)
    return chunks or [text]


def parse_script_segments(theme: str, total_seconds: float) -> list[VideoSegment]:
    raw_segments = generate_script(theme)
    durations: list[float] = []

    for time_range, _, _ in raw_segments:
        numbers = [int(value) for value in re.findall(r"\d+", time_range)]
        if len(numbers) >= 2:
            durations.append(max(1, numbers[1] - numbers[0]))
        else:
            durations.append(1)

    duration_sum = sum(durations) or 1
    scaled = [duration / duration_sum * total_seconds for duration in durations]

    return [
        VideoSegment(shot=index, label=label, voiceover=voiceover, duration=scaled[index - 1])
        for index, (_, label, voiceover) in enumerate(raw_segments, start=1)
    ]


def build_caption_cues(theme: str, total_seconds: float) -> list[CaptionCue]:
    cues: list[CaptionCue] = []
    for segment in parse_script_segments(theme, total_seconds):
        chunks = split_voiceover(segment.voiceover)
        cue_duration = segment.duration / max(1, len(chunks))
        for chunk in chunks:
            cues.append(
                CaptionCue(
                    shot=segment.shot,
                    label=segment.label,
                    text=chunk,
                    duration=cue_duration,
                )
            )
    return cues


def wave_duration(path: Path) -> float:
    with wave.open(str(path), "rb") as handle:
        return handle.getnframes() / float(handle.getframerate())


def concat_wavs(wav_paths: list[Path], output_path: Path, pause_seconds: float) -> Path:
    if not wav_paths:
        raise ValueError("No wav files to concatenate.")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(wav_paths[0]), "rb") as first:
        params = first.getparams()

    silence_frames = int(params.framerate * pause_seconds)
    silence = b"\x00" * silence_frames * params.nchannels * params.sampwidth

    with wave.open(str(output_path), "wb") as output:
        output.setparams(params)
        for index, wav_path in enumerate(wav_paths):
            with wave.open(str(wav_path), "rb") as source:
                if source.getparams()[:3] != params[:3]:
                    raise ValueError(f"WAV format mismatch: {wav_path}")
                output.writeframes(source.readframes(source.getnframes()))
            if pause_seconds > 0 and index < len(wav_paths) - 1:
                output.writeframes(silence)

    return output_path


def synthesize_aligned_voice(
    cues: list[CaptionCue],
    temp_root: Path,
    temp_stem: str,
    voice_keyword: str,
    rate: int,
    pause_seconds: float,
) -> tuple[list[CaptionCue], Path]:
    wav_paths: list[Path] = []
    aligned: list[CaptionCue] = []

    for index, cue in enumerate(cues, start=1):
        wav_path = temp_root / f"{temp_stem}.{index:03d}.wav"
        synthesize_sapi_wav(cue.text, wav_path, voice_keyword=voice_keyword, rate=rate)
        duration = wave_duration(wav_path)
        wav_paths.append(wav_path)
        aligned.append(
            CaptionCue(
                shot=cue.shot,
                label=cue.label,
                text=cue.text,
                duration=max(0.25, duration + pause_seconds),
            )
        )

    audio_path = temp_root / f"{temp_stem}.aligned.wav"
    concat_wavs(wav_paths, audio_path, pause_seconds=pause_seconds)
    return aligned, audio_path


def make_canvas(width: int, height: int) -> Image.Image:
    return Image.new("RGB", (width, height), (248, 247, 242))


def draw_line(draw: ImageDraw.ImageDraw, points: list[tuple[float, float]], width: int = 5) -> None:
    draw.line([(int(x), int(y)) for x, y in points], fill=(30, 32, 34), width=width, joint="curve")


def draw_stickman(
    draw: ImageDraw.ImageDraw,
    center_x: float,
    base_y: float,
    scale: float = 1.0,
    pose: float = 0.0,
    color: tuple[int, int, int] = (28, 30, 32),
) -> None:
    head_r = 34 * scale
    head_y = base_y - 230 * scale
    neck_y = head_y + head_r
    hip_y = base_y - 95 * scale
    foot_y = base_y
    arm_swing = math.sin(pose * math.tau) * 22 * scale

    draw.ellipse(
        [center_x - head_r, head_y - head_r, center_x + head_r, head_y + head_r],
        outline=color,
        width=max(3, int(5 * scale)),
    )
    draw_line(draw, [(center_x, neck_y), (center_x, hip_y)], width=max(3, int(5 * scale)))
    draw_line(
        draw,
        [
            (center_x, neck_y + 25 * scale),
            (center_x - 78 * scale, neck_y + 75 * scale + arm_swing),
        ],
        width=max(3, int(5 * scale)),
    )
    draw_line(
        draw,
        [
            (center_x, neck_y + 25 * scale),
            (center_x + 78 * scale, neck_y + 75 * scale - arm_swing),
        ],
        width=max(3, int(5 * scale)),
    )
    draw_line(
        draw,
        [(center_x, hip_y), (center_x - 68 * scale, foot_y)],
        width=max(3, int(5 * scale)),
    )
    draw_line(
        draw,
        [(center_x, hip_y), (center_x + 68 * scale, foot_y)],
        width=max(3, int(5 * scale)),
    )


def draw_thought_bubble(
    draw: ImageDraw.ImageDraw,
    x: float,
    y: float,
    radius: float,
    text: str | None = None,
    font: ImageFont.ImageFont | None = None,
) -> None:
    bounds = [x - radius, y - radius * 0.7, x + radius, y + radius * 0.7]
    draw.ellipse(bounds, outline=(48, 50, 52), width=4)
    if text and font:
        w = text_width(font, text)
        draw.text((x - w / 2, y - 13), text, fill=(48, 50, 52), font=font)


def draw_scene_one(draw: ImageDraw.ImageDraw, width: int, height: int, progress: float, fonts: Fonts) -> None:
    desk_y = height * 0.66
    draw.rounded_rectangle(
        [width * 0.18, desk_y, width * 0.82, desk_y + 34],
        radius=12,
        fill=(218, 208, 190),
        outline=(45, 45, 45),
        width=4,
    )
    draw_stickman(draw, width * 0.5, desk_y + 18, scale=1.05, pose=progress)
    for index in range(6):
        angle = progress * math.tau + index * math.tau / 6
        x = width * 0.5 + math.cos(angle) * width * 0.28
        y = height * 0.28 + math.sin(angle * 1.4) * height * 0.07
        draw_thought_bubble(draw, x, y, 42 + index % 2 * 10, "想?" if index == 1 else None, fonts.small)


def draw_scene_two(draw: ImageDraw.ImageDraw, width: int, height: int, progress: float, fonts: Fonts) -> None:
    lens_x = width * 0.53
    lens_y = height * 0.36
    lens_r = width * 0.24
    draw.ellipse(
        [lens_x - lens_r, lens_y - lens_r, lens_x + lens_r, lens_y + lens_r],
        outline=(30, 32, 34),
        width=9,
    )
    draw_line(draw, [(lens_x + lens_r * 0.68, lens_y + lens_r * 0.68), (width * 0.82, height * 0.61)], 10)
    for index, dx in enumerate([-0.12, 0.0, 0.12]):
        face_x = lens_x + width * dx
        face_y = lens_y + math.sin(progress * math.tau + index) * 12
        draw.ellipse([face_x - 30, face_y - 30, face_x + 30, face_y + 30], outline=(55, 55, 55), width=4)
        draw.arc([face_x - 14, face_y - 4, face_x + 14, face_y + 20], 15, 165, fill=(55, 55, 55), width=3)
        draw.point((face_x - 10, face_y - 5), fill=(55, 55, 55))
        draw.point((face_x + 10, face_y - 5), fill=(55, 55, 55))
    draw_stickman(draw, width * 0.32, height * 0.76, scale=0.8, pose=progress + 0.2)


def draw_scene_three(draw: ImageDraw.ImageDraw, width: int, height: int, progress: float, fonts: Fonts) -> None:
    mid = width // 2
    draw.rectangle([0, height * 0.17, mid, height * 0.73], fill=(239, 235, 225))
    draw.rectangle([mid, height * 0.17, width, height * 0.73], fill=(240, 247, 242))
    draw.line([mid, height * 0.17, mid, height * 0.73], fill=(60, 60, 60), width=4)
    for index in range(7):
        x = width * 0.12 + index * width * 0.055
        y = height * 0.33 + math.sin(progress * math.tau + index) * 44
        draw.arc([x - 30, y - 30, x + 30, y + 30], 20, 300, fill=(70, 70, 70), width=4)
    draw.ellipse([mid + 80, height * 0.25, mid + 180, height * 0.35], outline=(55, 55, 55), width=4)
    window_left = mid + width * 0.13
    window_right = width - width * 0.13
    draw.rectangle([window_left, height * 0.43, window_right, height * 0.55], outline=(55, 55, 55), width=4)
    draw.line([window_left + width * 0.03, height * 0.49, window_right - width * 0.03, height * 0.49], fill=(55, 55, 55), width=3)
    draw_stickman(draw, width * 0.5, height * 0.82, scale=0.95, pose=progress)
    draw.text((width * 0.1, height * 0.2), "脑补", fill=(50, 50, 50), font=fonts.label)
    draw.text((mid + width * 0.11, height * 0.2), "现实", fill=(50, 50, 50), font=fonts.label)


def draw_scene_four(draw: ImageDraw.ImageDraw, width: int, height: int, progress: float, fonts: Fonts) -> None:
    note = [width * 0.18, height * 0.2, width * 0.82, height * 0.53]
    draw.rounded_rectangle(note, radius=22, fill=(255, 248, 190), outline=(55, 55, 55), width=5)
    questions = ["是真的吗？", "重要吗？", "最小一步？"]
    for index, text in enumerate(questions):
        y = height * 0.26 + index * height * 0.085
        draw.text((width * 0.25, y), text, fill=(42, 42, 42), font=fonts.label)
        draw.line([width * 0.23, y + 34, width * 0.73, y + 34], fill=(115, 100, 70), width=2)
    draw_stickman(draw, width * 0.5, height * 0.86, scale=0.95, pose=progress)
    check_x = width * 0.71
    check_y = height * 0.45 + math.sin(progress * math.tau) * 5
    draw_line(draw, [(check_x, check_y), (check_x + 18, check_y + 20), (check_x + 62, check_y - 36)], 7)


def draw_scene_five(draw: ImageDraw.ImageDraw, width: int, height: int, progress: float, fonts: Fonts) -> None:
    draw.rectangle([0, height * 0.16, width, height * 0.8], fill=(235, 234, 225))
    spotlight_x = width * (0.35 + progress * 0.25)
    draw.ellipse(
        [spotlight_x - width * 0.34, height * 0.16, spotlight_x + width * 0.34, height * 0.77],
        fill=(255, 252, 232),
        outline=(180, 170, 132),
        width=4,
    )
    for index in range(5):
        alpha = 120 - index * 18
        x = width * (0.18 + index * 0.15)
        y = height * (0.28 + 0.05 * math.sin(progress * math.tau + index))
        shade = max(120, 230 - alpha)
        draw.ellipse([x - 22, y - 15, x + 22, y + 15], outline=(shade, shade, shade), width=3)
    draw.line([width * 0.18, height * 0.78, width * 0.84, height * 0.78], fill=(45, 45, 45), width=4)
    draw_stickman(draw, spotlight_x, height * 0.77, scale=0.9, pose=progress)
    draw.text((width * 0.17, height * 0.19), "把注意力拿回来", fill=(40, 40, 40), font=fonts.title)


def draw_header(draw: ImageDraw.ImageDraw, width: int, title: str, segment: CaptionCue, fonts: Fonts) -> None:
    margin = int(width * 0.07)
    draw.text((margin, 36), f"镜头 {segment.shot} · {segment.label}", fill=(100, 86, 64), font=fonts.small)
    lines = wrap_text(title, fonts.title, width - margin * 2)
    for index, line in enumerate(lines[:2]):
        draw.text((margin, 70 + index * 46), line, fill=(32, 34, 36), font=fonts.title)


def draw_subtitle(
    image: Image.Image,
    text: str,
    fonts: Fonts,
    max_lines: int = 3,
) -> None:
    width, height = image.size
    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    margin = int(width * 0.065)
    box_h = int(height * 0.18)
    box_y = height - box_h - int(height * 0.04)
    draw.rounded_rectangle(
        [margin, box_y, width - margin, box_y + box_h],
        radius=26,
        fill=(255, 255, 255, 228),
        outline=(36, 36, 36, 220),
        width=3,
    )
    lines = wrap_text(text, fonts.subtitle, width - margin * 2 - 52)[:max_lines]
    line_height = fonts.subtitle.getbbox("国")[3] - fonts.subtitle.getbbox("国")[1] + 10
    start_y = box_y + (box_h - line_height * len(lines)) / 2
    text_draw = ImageDraw.Draw(overlay)
    for index, line in enumerate(lines):
        line_w = text_width(fonts.subtitle, line)
        text_draw.text(
            ((width - line_w) / 2, start_y + index * line_height),
            line,
            fill=(22, 22, 22, 255),
            font=fonts.subtitle,
        )
    image.alpha_composite(overlay)


def draw_progress_bar(draw: ImageDraw.ImageDraw, width: int, height: int, progress: float) -> None:
    margin = int(width * 0.07)
    y = height - 18
    draw.rounded_rectangle([margin, y, width - margin, y + 6], radius=4, fill=(220, 217, 209))
    draw.rounded_rectangle(
        [margin, y, margin + (width - margin * 2) * progress, y + 6],
        radius=4,
        fill=(38, 38, 38),
    )


def render_frame(
    width: int,
    height: int,
    title: str,
    cue: CaptionCue,
    segment_progress: float,
    video_progress: float,
    fonts: Fonts,
) -> Image.Image:
    image = make_canvas(width, height).convert("RGBA")
    draw = ImageDraw.Draw(image)
    draw_header(draw, width, title, cue, fonts)

    scene_drawers = {
        1: draw_scene_one,
        2: draw_scene_two,
        3: draw_scene_three,
        4: draw_scene_four,
        5: draw_scene_five,
    }
    scene_drawers.get(cue.shot, draw_scene_one)(draw, width, height, segment_progress, fonts)

    draw_subtitle(image, cue.text, fonts)
    draw_progress_bar(ImageDraw.Draw(image), width, height, video_progress)
    return image.convert("RGB")


def render_video(
    theme: str,
    output_path: Path,
    total_seconds: float = 60,
    fps: int = 12,
    width: int = 720,
    height: int = 1280,
    with_voice: bool = False,
    voice_keyword: str = "Chinese",
    voice_rate: int = 0,
) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fonts = build_fonts(width)
    title = generate_titles(theme)[0]
    cues = build_caption_cues(theme, total_seconds)
    temp_stem = hashlib.sha1(str(output_path).encode("utf-8")).hexdigest()[:12]
    temp_root = default_tts_temp_root()
    temp_root.mkdir(parents=True, exist_ok=True)
    render_path = temp_root / f"{temp_stem}.silent{output_path.suffix}" if with_voice else output_path

    audio_path: Path | None = None
    if with_voice:
        cues, audio_path = synthesize_aligned_voice(
            cues,
            temp_root=temp_root,
            temp_stem=temp_stem,
            voice_keyword=voice_keyword,
            rate=voice_rate,
            pause_seconds=0.12,
        )
        total_seconds = sum(cue.duration for cue in cues)

    total_frames = max(1, int(total_seconds * fps))
    timeline: list[tuple[float, float, CaptionCue]] = []
    cursor = 0.0
    shot_bounds: dict[int, list[float]] = {}
    for cue in cues:
        start = cursor
        end = cursor + cue.duration
        timeline.append((start, end, cue))
        if cue.shot not in shot_bounds:
            shot_bounds[cue.shot] = [start, end]
        else:
            shot_bounds[cue.shot][1] = end
        cursor = end

    writer = imageio.get_writer(
        str(render_path),
        fps=fps,
        codec="libx264",
        pixelformat="yuv420p",
        output_params=["-movflags", "faststart"],
        macro_block_size=1,
    )

    try:
        last_bucket = -1
        for frame_index in range(total_frames):
            current_time = frame_index / fps
            start, end, cue = timeline[-1]
            for item in timeline:
                if item[0] <= current_time < item[1]:
                    start, end, cue = item
                    break

            shot_start, shot_end = shot_bounds[cue.shot]
            segment_progress = min(
                1.0,
                max(0.0, (current_time - shot_start) / max(0.01, shot_end - shot_start)),
            )
            video_progress = min(1.0, frame_index / max(1, total_frames - 1))
            frame = render_frame(width, height, title, cue, segment_progress, video_progress, fonts)
            writer.append_data(np.asarray(frame))

            bucket = int(video_progress * 10)
            if bucket != last_bucket:
                print(f"rendering {bucket * 10}%")
                last_bucket = bucket
    finally:
        writer.close()

    if with_voice and audio_path:
        mux_audio(render_path, audio_path, output_path, total_seconds=total_seconds)

    return output_path


def default_tts_temp_root() -> Path:
    for parent in PROJECT_ROOT.parents:
        if str(parent).isascii():
            return parent / "stickman_content_factory_tts"
    return Path(tempfile.gettempdir()) / "stickman_content_factory_tts"


def ps_quote(path: Path) -> str:
    return "'" + str(path).replace("'", "''") + "'"


def synthesize_sapi_wav(text: str, wav_path: Path, voice_keyword: str = "Chinese", rate: int = 0) -> Path:
    wav_path.parent.mkdir(parents=True, exist_ok=True)
    text_path = wav_path.with_suffix(".voice.txt")
    script_path = wav_path.with_suffix(".voice.ps1")
    text_path.write_text(text, encoding="utf-8-sig")

    script = f"""
$ErrorActionPreference = 'Stop'
$text = Get-Content -Raw -Encoding UTF8 -LiteralPath {ps_quote(text_path)}
$voice = New-Object -ComObject SAPI.SpVoice
$selected = $null
foreach ($candidate in $voice.GetVoices()) {{
    if ($candidate.GetDescription() -like '*{voice_keyword}*') {{
        $selected = $candidate
        break
    }}
}}
if ($selected -ne $null) {{
    $voice.Voice = $selected
}}
$voice.Rate = {rate}
$voice.Volume = 100
$stream = New-Object -ComObject SAPI.SpFileStream
$stream.Open({ps_quote(wav_path)}, 3, $false)
$voice.AudioOutputStream = $stream
$voice.Speak($text) | Out-Null
$stream.Close()
""".strip()
    script_path.write_text(script, encoding="utf-8-sig")

    subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(script_path),
        ],
        check=True,
    )
    return wav_path


def mux_audio(video_path: Path, audio_path: Path, output_path: Path, total_seconds: float) -> Path:
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    subprocess.run(
        [
            ffmpeg,
            "-y",
            "-i",
            str(video_path),
            "-i",
            str(audio_path),
            "-t",
            str(total_seconds),
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-b:a",
            "128k",
            "-movflags",
            "faststart",
            str(output_path),
        ],
        check=True,
    )
    return output_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate a simple stickman vertical short video.")
    parser.add_argument("theme", nargs="?", help="短视频主题")
    parser.add_argument("--batch30", action="store_true", help="批量生成内置 30 个主题")
    parser.add_argument("--topic-file", type=Path, help="从主题文件读取， 每行一个主题")
    parser.add_argument("--limit", type=int, help="限制批量生成数量，适合测试")
    parser.add_argument("--seconds", type=float, default=60, help="视频时长，默认 60 秒")
    parser.add_argument("--fps", type=int, default=12, help="帧率，默认 12")
    parser.add_argument("--width", type=int, default=720, help="视频宽度，默认 720")
    parser.add_argument("--height", type=int, default=1280, help="视频高度，默认 1280")
    parser.add_argument("--out", type=Path, default=Path("outputs/videos"), help="输出目录")
    parser.add_argument("--voice", action="store_true", help="使用 Windows SAPI 生成本地配音")
    parser.add_argument("--voice-keyword", default="Chinese", help="SAPI voice description keyword")
    parser.add_argument("--voice-rate", type=int, default=0, help="SAPI 语速，范围通常为 -10 到 10")
    return parser.parse_args()


def resolve_themes(args: argparse.Namespace) -> list[str]:
    if args.batch30:
        themes = list(DEFAULT_TOPICS)
    elif args.topic_file:
        themes = read_topics_file(args.topic_file)
    elif args.theme:
        themes = [args.theme]
    else:
        raise SystemExit("Please provide a theme, --batch30, or --topic-file.")

    if args.limit is not None:
        if args.limit <= 0:
            raise SystemExit("--limit must be greater than 0.")
        themes = themes[: args.limit]

    if not themes:
        raise SystemExit("No themes to render.")
    return themes


def main() -> None:
    args = parse_args()
    themes = resolve_themes(args)
    batch_mode = len(themes) > 1

    for index, theme in enumerate(themes, start=1):
        slug = sanitize_filename(theme)
        filename = f"{index:03d}_{slug}.mp4" if batch_mode else f"{slug}.mp4"
        output_path = args.out / filename
        print(f"[{index}/{len(themes)}] rendering: {theme}")
        rendered = render_video(
            theme=theme,
            output_path=output_path,
            total_seconds=args.seconds,
            fps=args.fps,
            width=args.width,
            height=args.height,
            with_voice=args.voice,
            voice_keyword=args.voice_keyword,
            voice_rate=args.voice_rate,
        )
        print(f"video generated: {rendered}")


if __name__ == "__main__":
    main()
