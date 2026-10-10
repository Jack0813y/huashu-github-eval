# huashu-github-eval

GitHub 的评价指标不止 star：用多维度指标给花叔（alchaincyf）的 5 个主要项目打分，并用 3 个传统工程项目作对照。

数据拉取时间：2026-10-10 13:18 UTC。

## 评分对象

- 目标组：`alchaincyf/nuwa-skill`、`alchaincyf/huashu-design`、`alchaincyf/zhangxuefeng-skill`、`alchaincyf/darwin-skill`、`alchaincyf/hermes-agent-orange-book`
- 对照组：`sharkdp/hyperfine`、`dandavison/delta`、`ajeetdsouza/zoxide`

对照组都是个人账号名下的项目。组织账号的项目里，维护者用个人账号提交代码，会被误算成"外部贡献"。

## 方法

1. **定权重**：把 `judge_prompt.md` 里的 prompt 分别发给 Claude、ChatGPT、Gemini、Grok。prompt 里不提评分对象，也不给数据。每家只跑了一次，权重记录在 `weights.json` 里，另附一组"等权示例"作为基准。
2. **拉数据**：`fetch_metrics.py` 通过 GitHub API 拉取 11 项指标，输出 `metrics.csv` 和 `metrics.json`。
3. **算分**：`score.py` 先把各项指标缩放到 0–100，再按各家权重求和，输出 `scores.csv` 和 `normalized.csv`。star 这类数量类指标先取对数；days_since_push 越小越好。

分数是这 8 个仓库之间的相对分，换一批对照组，分数会变。

## 文件

| 文件 | 内容 |
|---|---|
| `fetch_metrics.py` | 拉取 GitHub 数据，只用 Python 标准库 |
| `score.py` | 归一化并按权重算分 |
| `judge_prompt.md` | 给 AI 裁判的盲评 prompt |
| `weights.json` | 四家 AI 的权重和等权基准 |
| `metrics.csv` / `metrics.json` | 原始指标数据 |
| `normalized.csv` | 各指标归一化后的 0–100 分 |
| `scores.csv` | 最终得分和排名 |

## 复现

```bash
export GITHUB_TOKEN=你的token   # 可选，不设也能跑，只是更慢
python3 fetch_metrics.py
python3 score.py
```

重新拉取的数据会和这里的快照不同，因为 star 等指标一直在变。

## 局限

- 目标组项目只有大约 6 个月，对照组有 6 到 9 年。issue、PR、release 这类累计指标对老项目有利。
- 部分比例的样本很小，比如 hermes-agent-orange-book 一共只有 5 个 issue。
- 每个 AI 只跑了一次，多问几次权重可能会有出入。
- 内容型仓库本来就不太需要别人提交代码，用共建指标衡量它们天然吃亏。
