from __future__ import annotations

import argparse
import hashlib
import re
from datetime import datetime
from pathlib import Path


DEFAULT_TOPICS = [
    "总担心别人怎么看我",
    "一犯错就反复复盘",
    "总觉得自己不够好",
    "害怕拒绝别人",
    "消息发出去后反复检查",
    "总想把事情做到完美才开始",
    "别人一句话就影响一整天",
    "总觉得休息是在浪费时间",
    "害怕被讨厌所以一直讨好",
    "做决定前反复纠结",
    "还没开始就担心失败",
    "总拿自己和别人比较",
    "不敢表达真实想法",
    "明明很累却停不下来",
    "害怕麻烦别人",
    "总觉得自己应该更努力",
    "看到别人成功就焦虑",
    "总为还没发生的事担心",
    "把别人的情绪都揽到自己身上",
    "拖延后又疯狂自责",
    "不敢发作品怕被评价",
    "总想证明自己值得被爱",
    "计划太多行动太少",
    "害怕冲突所以一直忍",
    "总觉得错过了最佳时机",
    "对未来没有安全感",
    "睡前脑子停不下来",
    "被冷落后开始自我怀疑",
    "总想控制所有结果",
    "把小问题想成大灾难",
]


CORE_TOPICS = [
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
    *DEFAULT_TOPICS,
]


TITLE_PATTERNS = [
    "你不是想太多，是把「{theme}」看得太重了",
    "当你{theme}，先别急着骂自己",
    "停止内耗：处理「{theme}」的一个小方法",
    "越在意「{theme}」，越要练习这件事",
    "真正困住你的，不是别人，是反复脑补",
    "如果你也{theme}，请记住这句话",
    "把注意力从别人身上拿回来",
    "别再用「{theme}」消耗自己了",
    "你可以敏感，但不用一直受伤",
    "3秒钟，把自己从内耗里拉出来",
]


COVER_PATTERNS = [
    "别让脑补\n替你生活",
    "你没那么糟\n别人也没那么忙着看你",
    "停止内耗\n从这一秒开始",
    "把注意力\n还给自己",
    "敏感的人\n也可以很松弛",
]


def extract_theme_parts(theme: str) -> dict[str, str]:
    scenario = ""
    hook = ""
    body = theme.strip()

    if "，" in body:
        possible_scenario, body = body.split("，", 1)
        if 2 <= len(possible_scenario) <= 12:
            scenario = possible_scenario
        else:
            body = f"{possible_scenario}，{body}"

    if "：" in body:
        body, hook = body.split("：", 1)

    core_topic = ""
    for topic in sorted(CORE_TOPICS, key=len, reverse=True):
        if topic in theme:
            core_topic = topic
            break

    if not core_topic:
        core_topic = body.strip() or theme.strip()
        core_topic = re.sub(r"^(为什么你会|送给正在|停止用|每天1分钟减少|如果火柴人也会|给|从)", "", core_topic)
        core_topic = re.sub(
            r"(的人最容易掉进的一个坑|其实不是懒也不是玻璃心|时先做这个3秒动作|的你一句话|消耗自己|背后的真实需求|的人一个小练习|时别急着讨好所有人|不代表你没有价值|时大脑正在骗你|到自我接纳)$",
            "",
            core_topic,
        )

    return {
        "scenario": scenario.strip(),
        "topic": core_topic.strip("，。： "),
        "hook": hook.strip(),
    }


def theme_opening(theme: str) -> str:
    parts = extract_theme_parts(theme)
    topic = parts["topic"]
    scenario = parts["scenario"]
    hook = parts["hook"]

    if scenario and hook:
        return f"{scenario}，你又被「{topic}」困住，心里还不停提醒自己：{hook}"
    if scenario:
        return f"{scenario}，你又被「{topic}」困住"
    return topic


def sanitize_filename(text: str, fallback_prefix: str = "topic") -> str:
    name = re.sub(r"\s+", "-", text.strip())
    name = re.sub(r'[\\/:*?"<>|]+', "", name)
    name = re.sub(r"-{2,}", "-", name).strip("-_.")
    if name:
        return name[:80]
    digest = hashlib.sha1(text.encode("utf-8")).hexdigest()[:8]
    return f"{fallback_prefix}-{digest}"


def unique_preserve_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result


def generate_titles(theme: str) -> list[str]:
    parts = extract_theme_parts(theme)
    topic = parts["topic"]
    scenario = parts["scenario"]
    hook = parts["hook"]
    context = f"{scenario}，" if scenario else ""
    hook_title = f"{hook}，比硬撑更重要" if hook else f"{topic}时，先停3秒"

    return [
        f"{context}别让「{topic}」消耗你",
        f"{topic}的人，先别急着骂自己",
        f"被「{topic}」困住时，试试这招",
        "你不是脆弱，是太想被认可",
        f"{context}把注意力还给自己",
        f"{topic}时，先问自己这3句",
        "别把脑补当成事实",
        "敏感的人，也可以很松弛",
        hook_title,
        "3秒钟，把自己从内耗里拉出来",
    ]


def generate_script(theme: str) -> list[tuple[str, str, str]]:
    opening = theme_opening(theme)
    return [
        (
            "0-8秒",
            "共鸣开场",
            f"你有没有这种时候：{opening}。表面上你什么都没做，脑子里却已经开了十几场会议。",
        ),
        (
            "9-20秒",
            "指出内耗",
            "你反复想，不是因为你脆弱，而是因为你太想把每一种可能都提前处理好。",
        ),
        (
            "21-36秒",
            "认知反转",
            "但问题是，大脑会把想象当成任务。你越想控制别人的反应，就越失去自己的节奏。",
        ),
        (
            "37-50秒",
            "行动建议",
            "下次再开始内耗时，问自己三个问题：这是真的吗？这重要吗？我现在能做的最小一步是什么？",
        ),
        (
            "51-60秒",
            "结尾金句",
            "别人的眼光不是你的遥控器。把注意力拿回来，你的人生才会重新有声音。",
        ),
    ]


def generate_storyboard(theme: str) -> list[dict[str, str]]:
    opening = theme_opening(theme)
    return [
        {
            "shot": "1",
            "duration": "0-8秒",
            "scene": "白底极简房间，火柴人坐在桌前，头顶冒出很多对话气泡。",
            "action": "火柴人捂着头，气泡不断变多。",
            "emotion": "焦虑、紧绷",
            "voiceover": f"你有没有这种时候：{opening}。",
        },
        {
            "shot": "2",
            "duration": "9-20秒",
            "scene": "火柴人面前出现一个巨大的放大镜，放大镜里是别人的表情。",
            "action": "火柴人盯着放大镜，身体越来越小。",
            "emotion": "自我怀疑",
            "voiceover": "你反复想，是因为太想提前处理好所有可能。",
        },
        {
            "shot": "3",
            "duration": "21-36秒",
            "scene": "画面切成两半：左边是脑补风暴，右边是真实世界安静如常。",
            "action": "火柴人停下来，看见两边差别。",
            "emotion": "恍然、松动",
            "voiceover": "大脑会把想象当成任务，但想象不等于现实。",
        },
        {
            "shot": "4",
            "duration": "37-50秒",
            "scene": "火柴人手里拿着一张小纸条，上面写着三个问题。",
            "action": "火柴人把气泡一个个擦掉，只留下脚下的一小步。",
            "emotion": "稳定、清醒",
            "voiceover": "问自己：是真的吗？重要吗？我现在能做的最小一步是什么？",
        },
        {
            "shot": "5",
            "duration": "51-60秒",
            "scene": "火柴人走出画面中央的聚光灯，背后气泡消散。",
            "action": "火柴人抬头向前走，画面出现结尾金句。",
            "emotion": "释然、有力量",
            "voiceover": "别人的眼光不是你的遥控器。把注意力拿回来。",
        },
    ]


def generate_stickman_prompts(theme: str) -> list[str]:
    prompts = []
    for item in generate_storyboard(theme):
        prompts.append(
            "极简黑白火柴人短视频画面，白色背景，线条干净，"
            f"镜头{item['shot']}，{item['scene']}，动作：{item['action']}，"
            f"情绪：{item['emotion']}，竖屏9:16，留出字幕安全区，无复杂背景，无文字水印"
        )
    return prompts


def generate_tags(theme: str) -> list[str]:
    base_tags = [
        "反内耗",
        "停止内耗",
        "心理成长",
        "情绪管理",
        "自我疗愈",
        "认知改变",
        "火柴人动画",
        "短视频脚本",
        "治愈系",
        "成长思维",
        "自我接纳",
        "松弛感",
    ]
    focus_tag = extract_theme_parts(theme)["topic"]
    theme_words = re.split(r"[，,。！？!?、\s]+", theme)
    theme_tags = [word for word in theme_words if 2 <= len(word) <= 10]
    return unique_preserve_order([focus_tag] + theme_tags + base_tags)[:15]


def generate_markdown(theme: str) -> str:
    titles = generate_titles(theme)
    script = generate_script(theme)
    storyboard = generate_storyboard(theme)
    drawing_prompts = generate_stickman_prompts(theme)
    covers = COVER_PATTERNS
    tags = generate_tags(theme)

    lines: list[str] = []
    lines.append(f"# 反内耗主题：{theme}")
    lines.append("")
    lines.append("## 1. 爆款标题10个")
    lines.extend([f"{index}. {title}" for index, title in enumerate(titles, start=1)])
    lines.append("")
    lines.append("## 2. 60秒文案")
    lines.append("| 时间 | 结构 | 旁白 |")
    lines.append("| --- | --- | --- |")
    for time_range, structure, voiceover in script:
        lines.append(f"| {time_range} | {structure} | {voiceover} |")
    lines.append("")
    lines.append("## 3. 5镜头分镜")
    lines.append("| 镜头 | 时长 | 画面 | 动作 | 情绪 | 旁白 |")
    lines.append("| --- | --- | --- | --- | --- | --- |")
    for item in storyboard:
        lines.append(
            "| {shot} | {duration} | {scene} | {action} | {emotion} | {voiceover} |".format(
                **item
            )
        )
    lines.append("")
    lines.append("## 4. 火柴人绘图Prompt")
    for index, prompt in enumerate(drawing_prompts, start=1):
        lines.append(f"{index}. {prompt}")
    lines.append("")
    lines.append("## 5. 封面文案")
    for index, cover in enumerate(covers, start=1):
        lines.append(f"{index}. {cover.replace(chr(10), ' / ')}")
    lines.append("")
    lines.append("## 6. 标签")
    lines.append(" ".join(f"#{tag}" for tag in tags))
    lines.append("")
    lines.append("## 发布文案")
    lines.append(
        f"如果你也经常被「{extract_theme_parts(theme)['topic']}」困住，先别急着责备自己。把注意力从脑补里拿回来，做一个能让当下变清晰的小动作。"
    )
    lines.append("")
    return "\n".join(lines)


def write_single_output(theme: str, output_dir: Path, prefix: str | None = None) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    filename = sanitize_filename(theme)
    if prefix:
        filename = f"{prefix}_{filename}"
    path = output_dir / f"{filename}.md"
    path.write_text(generate_markdown(theme), encoding="utf-8")
    return path


def write_component_outputs(theme: str, outputs_root: Path) -> None:
    slug = sanitize_filename(theme)
    scripts_dir = outputs_root / "scripts"
    storyboards_dir = outputs_root / "storyboards"
    prompts_dir = outputs_root / "prompts"
    for directory in (scripts_dir, storyboards_dir, prompts_dir):
        directory.mkdir(parents=True, exist_ok=True)

    script_lines = [f"# 60秒文案：{theme}", "", "| 时间 | 结构 | 旁白 |", "| --- | --- | --- |"]
    for time_range, structure, voiceover in generate_script(theme):
        script_lines.append(f"| {time_range} | {structure} | {voiceover} |")
    (scripts_dir / f"{slug}.md").write_text("\n".join(script_lines) + "\n", encoding="utf-8")

    storyboard_lines = [
        f"# 5镜头分镜：{theme}",
        "",
        "| 镜头 | 时长 | 画面 | 动作 | 情绪 | 旁白 |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for item in generate_storyboard(theme):
        storyboard_lines.append(
            "| {shot} | {duration} | {scene} | {action} | {emotion} | {voiceover} |".format(
                **item
            )
        )
    (storyboards_dir / f"{slug}.md").write_text(
        "\n".join(storyboard_lines) + "\n", encoding="utf-8"
    )

    prompt_lines = [f"# 火柴人绘图Prompt：{theme}", ""]
    prompt_lines.extend(
        f"{index}. {prompt}" for index, prompt in enumerate(generate_stickman_prompts(theme), start=1)
    )
    (prompts_dir / f"{slug}.md").write_text("\n".join(prompt_lines) + "\n", encoding="utf-8")


def read_topics_file(path: Path) -> list[str]:
    if not path.exists():
        raise FileNotFoundError(f"主题文件不存在：{path}")
    topics = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            topics.append(line)
    return topics


def write_batch(topics: list[str], outputs_root: Path) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    batch_dir = outputs_root / f"batch_{timestamp}"
    batch_dir.mkdir(parents=True, exist_ok=True)

    index_lines = ["# 批量生成索引", ""]
    for index, topic in enumerate(topics, start=1):
        path = write_single_output(topic, batch_dir, prefix=f"{index:02d}")
        write_component_outputs(topic, outputs_root)
        index_lines.append(f"{index}. [{topic}]({path.name})")

    (batch_dir / "index.md").write_text("\n".join(index_lines) + "\n", encoding="utf-8")
    return batch_dir


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="反内耗火柴人内容生产系统")
    parser.add_argument("theme", nargs="?", help="单个反内耗主题，例如：总担心别人怎么看我")
    parser.add_argument("--batch30", action="store_true", help="批量生成内置30个主题")
    parser.add_argument("--topic-file", type=Path, help="从文本文件读取主题，每行一个")
    parser.add_argument("--out", type=Path, default=Path("outputs"), help="输出目录，默认 outputs")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    outputs_root = args.out

    if args.batch30:
        batch_dir = write_batch(DEFAULT_TOPICS, outputs_root)
        print(f"已生成30个主题内容：{batch_dir}")
        return

    if args.topic_file:
        topics = read_topics_file(args.topic_file)
        if not topics:
            raise SystemExit("主题文件为空，请每行填写一个反内耗主题。")
        batch_dir = write_batch(topics, outputs_root)
        print(f"已生成{len(topics)}个主题内容：{batch_dir}")
        return

    if not args.theme:
        raise SystemExit("请提供一个主题，或使用 --batch30 / --topic-file。")

    content_dir = outputs_root / "content"
    path = write_single_output(args.theme, content_dir)
    write_component_outputs(args.theme, outputs_root)
    print(f"已生成内容：{path}")


if __name__ == "__main__":
    main()
