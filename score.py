#!/usr/bin/env python3
"""
读取 metrics.json 和 weights.json，按各 AI 裁判给的权重算分，输出 scores.csv。

用法：
    python3 score.py                  # 默认读 weights.json
    python3 score.py my_weights.json

归一化规则：
- 数量类指标（star、fork 等）先取 log(1+x)，再在所有参评仓库里 min-max 缩放到 0–100。
  不取 log 的话，3 万 star 会把其他维度全部压扁。
- 比例类指标（fork_rate、issue_close_rate）直接 min-max 缩放到 0–100。
- days_since_push 越小越好，缩放后取反。
注意：分数是「参评仓库之间的相对分」，换一批对照组，分数会变。
"""
import csv
import json
import math
import sys

# 参与打分的指标及其处理方式；键名要和给 AI 的 prompt、weights.json 保持一致
METRICS = {
    "stars": "log",
    "forks": "log",
    "fork_rate": "rate",
    "watchers": "log",
    "issues_closed": "log",
    "issue_close_rate": "rate",
    "prs_merged_external": "log",
    "external_contributors": "log",
    "commits_90d": "log",
    "releases": "log",
    "days_since_push": "inverse",
}


def normalize(repos):
    """返回 {repo: {metric: 0-100 分}}"""
    out = {r["repo"]: {} for r in repos}
    for m, kind in METRICS.items():
        raw = {}
        for r in repos:
            v = r.get(m)
            v = 0 if v is None else float(v)
            raw[r["repo"]] = math.log1p(v) if kind in ("log", "inverse") else v
        lo, hi = min(raw.values()), max(raw.values())
        for name, v in raw.items():
            s = 50.0 if hi == lo else (v - lo) / (hi - lo) * 100
            out[name][m] = 100 - s if kind == "inverse" else s
    return out


def load_weights(path):
    with open(path, encoding="utf-8") as f:
        judges = json.load(f)
    cleaned = {}
    for judge, w in judges.items():
        unknown = set(w) - set(METRICS)
        if unknown:
            print(f"警告：{judge} 有未知指标 {unknown}，已忽略", file=sys.stderr)
        w = {k: float(v) for k, v in w.items() if k in METRICS}
        total = sum(w.values())
        if total <= 0:
            print(f"警告：{judge} 权重全为 0，跳过", file=sys.stderr)
            continue
        if abs(total - 100) > 0.5:
            print(f"提示：{judge} 权重合计 {total:g}，已按比例缩放到 100", file=sys.stderr)
        cleaned[judge] = {k: v * 100 / total for k, v in w.items()}
    return cleaned


def main():
    weights_path = sys.argv[1] if len(sys.argv) > 1 else "weights.json"
    with open("metrics.json", encoding="utf-8") as f:
        repos = json.load(f)["repos"]
    judges = load_weights(weights_path)
    norm = normalize(repos)

    rows = []
    for r in repos:
        row = {"repo": r["repo"], "group": r["group"]}
        scores = []
        for judge, w in judges.items():
            s = sum(norm[r["repo"]][m] * w.get(m, 0) for m in METRICS) / 100
            row[judge] = round(s, 1)
            scores.append(s)
        row["平均分"] = round(sum(scores) / len(scores), 1) if scores else 0
        rows.append(row)
    rows.sort(key=lambda x: x["平均分"], reverse=True)

    # 打印结果表
    cols = ["repo", "group"] + list(judges) + ["平均分"]
    widths = {c: max(len(str(c)), *(len(str(r[c])) for r in rows)) + 2 for c in cols}
    print("".join(str(c).ljust(widths[c]) for c in cols))
    for r in rows:
        print("".join(str(r[c]).ljust(widths[c]) for c in cols))

    with open("scores.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)
    # 顺便导出各指标归一化后的分数，方便画雷达图
    with open("normalized.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=["repo"] + list(METRICS))
        w.writeheader()
        for name, ms in norm.items():
            w.writerow({"repo": name, **{k: round(v, 1) for k, v in ms.items()}})
    print("\n已写入 scores.csv 和 normalized.csv", file=sys.stderr)


if __name__ == "__main__":
    main()
