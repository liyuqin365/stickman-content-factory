from __future__ import annotations

import argparse
import csv
import hashlib
from collections import Counter
from datetime import date, datetime, timedelta
from pathlib import Path

from content_factory import (
    COVER_PATTERNS,
    generate_markdown,
    generate_script,
    generate_stickman_prompts,
    generate_storyboard,
    generate_tags,
    generate_titles,
    sanitize_filename,
)


BASE_TOPICS = [
    "总担心别人怎么看我",
    "讨好型人格",
    "拖延症",
    "完美主义",
    "害怕失败",
    "害怕开始",
    "总觉得自己不够好",
    "社交焦虑",
    "容貌焦虑",
    "年龄焦虑",
    "财富焦虑",
    "原生家庭影响",
    "情绪失控",
    "敏感人格",
    "总爱比较",
]


ANGLES = [
    ("共鸣", "为什么你会{topic}"),
    ("误区", "{topic}的人最容易掉进的一个坑"),
    ("反转", "{topic}其实不是懒也不是玻璃心"),
    ("行动", "{topic}时先做这个3秒动作"),
    ("金句", "送给正在{topic}的你一句话"),
    ("边界", "{topic}时如何把注意力拿回来"),
    ("复盘", "{topic}后别再这样责备自己"),
    ("自救", "{topic}的一个低成本自救方法"),
    ("清醒", "停止用{topic}消耗自己"),
    ("治愈", "{topic}的人也可以慢慢松下来"),
    ("场景", "当你又开始{topic}的时候"),
    ("习惯", "每天1分钟减少{topic}"),
    ("对话", "如果火柴人也会{topic}"),
    ("拆解", "{topic}背后的真实需求"),
    ("提醒", "{topic}不是你的错，但你可以换个做法"),
    ("练习", "给{topic}的人一个小练习"),
    ("关系", "{topic}时别急着讨好所有人"),
    ("自尊", "{topic}不代表你没有价值"),
    ("焦虑", "{topic}时大脑正在骗你"),
    ("成长", "从{topic}到自我接纳"),
]


SCENARIOS = [
    "发消息后",
    "开会发言前",
    "刷到别人动态时",
    "被朋友冷落时",
    "准备开始新任务时",
    "做错一件小事后",
    "晚上睡前",
    "收到否定评价时",
    "想拒绝别人时",
    "看到同龄人成功时",
    "准备发布作品前",
    "家人一句话之后",
    "独处时",
    "被催进度时",
    "做选择前",
    "照镜子时",
    "月底看账单时",
    "看到年龄数字时",
    "关系变冷时",
    "任务堆满时",
]


HOOKS = [
    "别急着骂自己",
    "你需要的是一个暂停键",
    "先把脑补停下来",
    "这不是你的全部",
    "你可以慢一点",
    "先做一个最小动作",
    "别把想象当事实",
    "把注意力还给自己",
    "你不需要证明所有事",
    "允许自己先完成再完美",
]


def read_base_topics(path: Path) -> list[str]:
    if not path.exists():
        return BASE_TOPICS

    topics: list[str] = []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.reader(handle)
        for row in reader:
            if not row:
                continue
            topic = row[0].strip()
            if topic and topic.lower() != "topic":
                topics.append(topic)

    return topics or BASE_TOPICS


def build_reserve_topics(base_topics: list[str], total: int) -> list[dict[str, str]]:
    quotas = {
        topic: total // len(base_topics) + (1 if index < total % len(base_topics) else 0)
        for index, topic in enumerate(base_topics)
    }
    candidates_by_topic: dict[str, list[dict[str, str]]] = {}

    for base_topic in base_topics:
        candidates: list[dict[str, str]] = []
        for angle_name, angle_template in ANGLES:
            for scenario in SCENARIOS:
                for hook in HOOKS:
                    theme = f"{scenario}，{angle_template.format(topic=base_topic)}：{hook}"
                    candidates.append(
                        {
                            "base_topic": base_topic,
                            "angle": angle_name,
                            "scenario": scenario,
                            "hook": hook,
                            "theme": theme,
                        }
                    )
        candidates.sort(
            key=lambda row: hashlib.sha1(
                f"{row['base_topic']}|{row['angle']}|{row['scenario']}|{row['hook']}".encode(
                    "utf-8"
                )
            ).hexdigest()
        )
        candidates_by_topic[base_topic] = candidates[: quotas[base_topic]]

    rows: list[dict[str, str]] = []
    max_quota = max(quotas.values())
    for round_index in range(max_quota):
        for base_topic in base_topics:
            selected = candidates_by_topic[base_topic]
            if round_index >= len(selected):
                continue
            row = selected[round_index].copy()
            row["id"] = f"{len(rows) + 1:04d}"
            rows.append(row)

    return rows


def distribute_days(total: int, days: int) -> list[int]:
    base = total // days
    extra = total % days
    return [base + (1 if index < extra else 0) for index in range(days)]


def build_schedule_rows(rows: list[dict[str, str]], start_day: date, days: int) -> list[dict[str, str]]:
    scheduled_rows: list[dict[str, str]] = []
    daily_counts = distribute_days(len(rows), days)
    cursor = 0
    for day_index, daily_target in enumerate(daily_counts, start=1):
        current_day = start_day + timedelta(days=day_index - 1)
        for _ in range(daily_target):
            row = rows[cursor].copy()
            row.update(
                {
                    "day": str(day_index),
                    "date": current_day.isoformat(),
                    "daily_target": str(daily_target),
                    "status": "draft_ready",
                }
            )
            scheduled_rows.append(row)
            cursor += 1
    return scheduled_rows


def write_topics_csv(rows: list[dict[str, str]], path: Path) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["id", "base_topic", "angle", "scenario", "hook", "theme"],
        )
        writer.writeheader()
        writer.writerows(rows)


def write_schedule_csv(rows: list[dict[str, str]], path: Path, start_day: date, days: int) -> None:
    scheduled_rows = build_schedule_rows(rows, start_day, days)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "day",
                "date",
                "daily_target",
                "content_id",
                "base_topic",
                "angle",
                "theme",
                "status",
            ],
        )
        writer.writeheader()
        for row in scheduled_rows:
            writer.writerow(
                {
                    "day": row["day"],
                    "date": row["date"],
                    "daily_target": row["daily_target"],
                    "content_id": row["id"],
                    "base_topic": row["base_topic"],
                    "angle": row["angle"],
                    "theme": row["theme"],
                    "status": row["status"],
                }
            )


def write_content_files(rows: list[dict[str, str]], content_dir: Path) -> list[Path]:
    content_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    for row in rows:
        filename = f"{row['id']}_{sanitize_filename(row['theme'])}.md"
        path = content_dir / filename
        path.write_text(generate_markdown(row["theme"]), encoding="utf-8")
        paths.append(path)
    return paths


def format_script(theme: str) -> str:
    return "\n".join(
        f"{time_range}｜{structure}｜{voiceover}"
        for time_range, structure, voiceover in generate_script(theme)
    )


def format_storyboard(theme: str) -> str:
    return "\n".join(
        "{shot}｜{duration}｜{scene}｜{action}｜{emotion}｜{voiceover}".format(**item)
        for item in generate_storyboard(theme)
    )


def write_notion_library_csv(
    rows: list[dict[str, str]],
    paths: list[Path],
    path: Path,
    start_day: date,
    days: int,
) -> None:
    scheduled_rows = build_schedule_rows(rows, start_day, days)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "Name",
                "Status",
                "Publish Date",
                "Day",
                "Daily Target",
                "Content ID",
                "Base Topic",
                "Angle",
                "Scenario",
                "Hook",
                "Theme",
                "Primary Title",
                "Cover Copy",
                "Tags",
                "Markdown File",
                "60s Copy",
                "Storyboard",
                "Drawing Prompts",
                "Publish Copy",
            ],
        )
        writer.writeheader()
        for row, content_path in zip(scheduled_rows, paths):
            theme = row["theme"]
            tags = " ".join(f"#{tag}" for tag in generate_tags(theme))
            writer.writerow(
                {
                    "Name": generate_titles(theme)[0],
                    "Status": "Draft Ready",
                    "Publish Date": row["date"],
                    "Day": row["day"],
                    "Daily Target": row["daily_target"],
                    "Content ID": row["id"],
                    "Base Topic": row["base_topic"],
                    "Angle": row["angle"],
                    "Scenario": row["scenario"],
                    "Hook": row["hook"],
                    "Theme": theme,
                    "Primary Title": generate_titles(theme)[0],
                    "Cover Copy": COVER_PATTERNS[0].replace("\n", " / "),
                    "Tags": tags,
                    "Markdown File": f"content/{content_path.name}",
                    "60s Copy": format_script(theme),
                    "Storyboard": format_storyboard(theme),
                    "Drawing Prompts": "\n".join(generate_stickman_prompts(theme)),
                    "Publish Copy": f"如果你也经常被「{row['base_topic']}」困住，先别急着责备自己。把注意力从脑补里拿回来，做一个能让当下变清晰的小动作。",
                }
            )


def write_index(rows: list[dict[str, str]], paths: list[Path], path: Path) -> None:
    lines = [
        "# 1000条火柴人内容储备索引",
        "",
        "| ID | 基础主题 | 角度 | 场景 | 内容稿 |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row, content_path in zip(rows, paths):
        lines.append(
            f"| {row['id']} | {row['base_topic']} | {row['angle']} | {row['scenario']} | [{row['theme']}](content/{content_path.name}) |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_summary(rows: list[dict[str, str]], path: Path, start_day: date, days: int) -> None:
    base_counts = Counter(row["base_topic"] for row in rows)
    angle_counts = Counter(row["angle"] for row in rows)
    daily_counts = distribute_days(len(rows), days)
    end_day = start_day + timedelta(days=days - 1)

    lines = [
        "# 3个月1000条火柴人内容储备",
        "",
        f"- 内容总数：{len(rows)}条",
        f"- 排期天数：{days}天",
        f"- 排期日期：{start_day.isoformat()} 至 {end_day.isoformat()}",
        f"- 日更节奏：{min(daily_counts)}-{max(daily_counts)}条/天",
        "- 单条内容包含：爆款标题10个、60秒文案、5镜头分镜、火柴人绘图Prompt、封面文案、标签、发布文案",
        "",
        "## 基础主题分布",
        "",
        "| 基础主题 | 数量 |",
        "| --- | --- |",
    ]
    for topic, count in base_counts.most_common():
        lines.append(f"| {topic} | {count} |")

    lines.extend(["", "## 内容角度分布", "", "| 角度 | 数量 |", "| --- | --- |"])
    for angle, count in angle_counts.most_common():
        lines.append(f"| {angle} | {count} |")

    lines.extend(
        [
            "",
            "## 文件",
            "",
            "- `topics_1000.csv`：1000条内容选题池",
            "- `calendar_90_days.csv`：90天生产排期",
            "- `notion_content_library.csv`：Notion内容库导入表",
            "- `content/`：1000篇完整 Markdown 内容稿",
            "- `index.md`：内容稿索引",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="生成3个月1000条火柴人内容储备")
    parser.add_argument("--topics", type=Path, default=Path("topics.csv"), help="基础主题CSV，默认 topics.csv")
    parser.add_argument("--total", type=int, default=1000, help="内容储备条数，默认1000")
    parser.add_argument("--days", type=int, default=90, help="排期天数，默认90")
    parser.add_argument("--start-date", default="2026-06-03", help="排期开始日期，格式 YYYY-MM-DD")
    parser.add_argument("--out", type=Path, default=Path("outputs/reserve_1000"), help="输出目录")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.total <= 0:
        raise SystemExit("--total 必须大于0")
    if args.days <= 0:
        raise SystemExit("--days 必须大于0")

    start_day = datetime.strptime(args.start_date, "%Y-%m-%d").date()
    base_topics = read_base_topics(args.topics)
    rows = build_reserve_topics(base_topics, args.total)
    if len(rows) < args.total:
        raise SystemExit(f"选题组合不足，只生成了 {len(rows)} 条。")

    args.out.mkdir(parents=True, exist_ok=True)
    write_topics_csv(rows, args.out / "topics_1000.csv")
    write_schedule_csv(rows, args.out / "calendar_90_days.csv", start_day, args.days)
    paths = write_content_files(rows, args.out / "content")
    write_notion_library_csv(rows, paths, args.out / "notion_content_library.csv", start_day, args.days)
    write_index(rows, paths, args.out / "index.md")
    write_summary(rows, args.out / "README.md", start_day, args.days)

    print(f"已生成{len(rows)}条火柴人内容储备：{args.out}")


if __name__ == "__main__":
    main()
