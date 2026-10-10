# 给 AI 裁判的盲评 prompt

使用方法：开一个**全新对话**，原样粘贴下面分隔线之间的内容。每个 AI 跑 3 次（每次新对话），记录三次结果。
不要告诉它要评谁的项目，也不要先给数据。

---

你是一名资深开源社区评审。我要为一批 GitHub 开源项目打一个综合分，衡量它们作为开源项目的「真实价值与健康度」。在看到任何具体数据之前，请你先确定各项指标的权重。

可用指标如下：

- stars：星标数（关注/收藏的人数）
- forks：被复刻的次数
- fork_rate：forks / stars，反映收藏者中有多少人真的拿去改或用
- watchers：订阅仓库动态的人数
- issues_closed：已关闭的 issue 数量（有人在用、在反馈，且问题被处理）
- issue_close_rate：已关闭 issue 占全部 issue 的比例（维护响应度）
- prs_merged_external：作者以外的人提交并被合并的 PR 数量（社区共建程度）
- external_contributors：作者以外的代码贡献者人数
- commits_90d：最近 90 天的提交次数（项目是否仍在活跃维护）
- releases：发布的正式版本数量（工程化程度）
- days_since_push：距最近一次推送的天数（越小越好）

要求：

1. 为以上 11 个指标分配权重，权重为整数，总和必须等于 100。可以给某项 0。
2. 每个指标附一句话说明理由。
3. 最后用两三句话说明你整体的评价哲学。
4. 在回答末尾，单独输出一个 JSON 代码块，只包含指标名和权重，格式如下：

```json
{"stars": 0, "forks": 0, "fork_rate": 0, "watchers": 0, "issues_closed": 0, "issue_close_rate": 0, "prs_merged_external": 0, "external_contributors": 0, "commits_90d": 0, "releases": 0, "days_since_push": 0}
```

---

## 把结果填进 weights.json

每个 AI 三次结果取平均（或三次分别记为 "Claude-1"、"Claude-2"…，score.py 会分别算分），填入 weights.json，然后运行 `python3 score.py`。
