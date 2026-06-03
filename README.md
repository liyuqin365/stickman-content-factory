# Stickman Content Factory

一个面向反内耗主题的火柴人短视频内容生产系统。

输入一个主题，例如：

```text
总担心别人怎么看我
```

自动生成：

1. 爆款标题10个
2. 60秒文案
3. 5镜头分镜
4. 火柴人绘图 Prompt
5. 封面文案
6. 标签
7. 发布文案

生成结果使用 Markdown 保存到 `outputs/`。

## 目录

```text
prompts/      提示词模板
skills/       内容角色和生产规则
topics/       批量主题样例
outputs/      生成结果
```

## 单主题生成

```powershell
python content_factory.py "总担心别人怎么看我"
```

输出：

- `outputs/content/总担心别人怎么看我.md`
- `outputs/scripts/总担心别人怎么看我.md`
- `outputs/storyboards/总担心别人怎么看我.md`
- `outputs/prompts/总担心别人怎么看我.md`

## 批量生成30个主题

```powershell
python content_factory.py --batch30
```

输出：

- `outputs/batch_日期时间/`
- `outputs/batch_日期时间/index.md`

## 从主题文件批量生成

每行一个主题：

```powershell
python content_factory.py --topic-file topics/anxiety.txt
```

也可以指定输出目录：

```powershell
python content_factory.py --batch30 --out outputs
```

## 提示词使用方式

`prompts/` 里的模板可以直接复制到任意大模型工具中使用，把 `{{theme}}` 替换成你的主题即可。

`skills/` 里的文件定义了内容生产时的角色、结构、风格和限制。

## 3个月1000条内容储备

使用根目录的 `topics.csv` 作为基础主题池，自动扩展出1000条火柴人内容角度，并生成90天生产排期：

```powershell
python reserve_factory.py
```

输出：

- `outputs/reserve_1000/topics_1000.csv`：1000条内容选题池
- `outputs/reserve_1000/calendar_90_days.csv`：90天生产排期
- `outputs/reserve_1000/notion_content_library.csv`：Notion内容库导入表
- `outputs/reserve_1000/content/`：1000篇完整 Markdown 内容稿
- `outputs/reserve_1000/index.md`：内容索引
- `outputs/reserve_1000/README.md`：储备统计摘要

## Codex + GitHub + Notion

- Codex：运行本项目生成内容。
- GitHub：使用 `.github/workflows/generate-reserve.yml` 手动或定时生成储备。
- Notion：导入 `outputs/reserve_1000/notion_content_library.csv` 作为内容库。

详细步骤见：

```text
docs/github-notion-setup.md
```
