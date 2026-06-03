# Codex + GitHub + Notion 内容库搭建

## 本地角色分工

- Codex：生成选题、脚本、分镜、绘图 Prompt、封面、标签、发布文案。
- GitHub：保存项目版本，运行 GitHub Actions，沉淀可追溯内容资产。
- Notion：作为内容库和排期看板，导入 `notion_content_library.csv` 后管理状态。

## GitHub

仓库建议名称：

```text
stickman-content-factory
```

推荐流程：

1. 把本目录推送到 GitHub 仓库。
2. 打开 Actions 页面。
3. 运行 `Generate Content Reserve` workflow。
4. 下载 workflow 生成的 `stickman-content-reserve` artifact。

当前工作流文件：

```text
.github/workflows/generate-reserve.yml
```

它会生成：

- `topics_1000.csv`
- `calendar_90_days.csv`
- `notion_content_library.csv`
- `content/` Markdown 内容稿
- `index.md`
- `README.md`

## Notion 内容库

在 Notion 中新建一个空页面，选择导入 CSV，上传：

```text
outputs/reserve_1000/notion_content_library.csv
```

建议字段类型：

| 字段 | 类型 |
| --- | --- |
| Name | Title |
| Status | Status |
| Publish Date | Date |
| Day | Number |
| Daily Target | Number |
| Content ID | Text |
| Base Topic | Select |
| Angle | Select |
| Scenario | Select |
| Hook | Text |
| Theme | Text |
| Primary Title | Text |
| Cover Copy | Text |
| Tags | Multi-select 或 Text |
| Markdown File | Text |
| 60s Copy | Text |
| Storyboard | Text |
| Drawing Prompts | Text |
| Publish Copy | Text |

推荐视图：

- Calendar：按 `Publish Date` 查看90天排期。
- Board：按 `Status` 管理生产状态。
- Table：按 `Base Topic`、`Angle`、`Scenario` 筛选内容。

## 状态流

```text
Idea -> Draft Ready -> Visual Prompt Ready -> Scheduled -> Published -> Repurposed
```

CSV 默认状态是 `Draft Ready`，导入 Notion 后可以批量修改。
