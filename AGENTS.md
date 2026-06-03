# Codex Project Guide

## Goal

Build and maintain a 3-month reserve of 1000 stickman-style anti-overthinking short-video content drafts.

## Core Commands

Generate one topic:

```powershell
python content_factory.py "总担心别人怎么看我"
```

Generate the 1000-item reserve and Notion import table:

```powershell
python reserve_factory.py
```

If the local `python` command is unavailable on Windows, use the Codex bundled Python runtime.

## Output Contract

Every content draft must include:

1. 爆款标题10个
2. 60秒文案
3. 5镜头分镜
4. 火柴人绘图Prompt
5. 封面文案
6. 标签
7. 发布文案

## Content Rules

- Keep the tone warm, concise, practical, and non-diagnostic.
- Use simple stickman-friendly scenes and actions.
- Preserve Markdown output.
- Keep Notion import data in CSV format.
- Store generated reserves under `outputs/reserve_1000/`.

## GitHub Automation

The workflow at `.github/workflows/generate-reserve.yml` generates the reserve as an artifact.

## Notion Library

Import `outputs/reserve_1000/notion_content_library.csv` into Notion as the content database.
