#!/usr/bin/env python3
"""
拉取 GitHub 仓库的多维度指标，输出 metrics.csv 和 metrics.json。

用法：
    export GITHUB_TOKEN=ghp_xxx      # 可选，强烈建议；不设也能跑，只是更慢
    python3 fetch_metrics.py

只用 Python 标准库，不需要 pip 安装任何东西。
"""
import csv
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

# ---------- 要评分的仓库，可自行增删 ----------
TARGETS = [
    "alchaincyf/nuwa-skill",
    "alchaincyf/huashu-design",
    "alchaincyf/zhangxuefeng-skill",
    "alchaincyf/darwin-skill",
    "alchaincyf/hermes-agent-orange-book",
]
# 对照组：同等 star 量级的传统工程型项目，可换成你觉得更合适的
CONTROLS = [
    "sharkdp/hyperfine",
    "dandavison/delta",
    "ajeetdsouza/zoxide",
]
# ----------------------------------------------

API = "https://api.github.com"
TOKEN = os.environ.get("GITHUB_TOKEN", "").strip()
# 搜索接口有单独限速：有 Token 每分钟 30 次，没有每分钟 10 次
SEARCH_PAUSE = 2.5 if TOKEN else 7.0


def request(path, params=None):
    """发请求，自动处理限速等待。返回 (数据, 响应头)。"""
    url = path if path.startswith("http") else API + path
    if params:
        url += "?" + urllib.parse.urlencode(params)
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "repo-metrics-script",
    }
    if TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"

    for attempt in range(6):
        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                body = r.read()
                return (json.loads(body) if body else None), r.headers
        except urllib.error.HTTPError as e:
            msg = e.read().decode("utf-8", "ignore")
            if e.code in (403, 429):
                retry_after = e.headers.get("Retry-After")
                remaining = e.headers.get("X-RateLimit-Remaining")
                reset = e.headers.get("X-RateLimit-Reset")
                if retry_after:
                    wait = int(retry_after)
                elif remaining == "0" and reset:
                    wait = max(int(reset) - time.time(), 0) + 2
                elif "secondary rate limit" in msg.lower():
                    wait = 60
                else:
                    raise RuntimeError(f"{e.code} {url}: {msg[:200]}")
                print(f"  触发限速，等待 {int(wait)} 秒……", file=sys.stderr)
                time.sleep(wait)
                continue
            raise RuntimeError(f"{e.code} {url}: {msg[:200]}")
        except urllib.error.URLError as e:
            if attempt < 3:
                time.sleep(3)
                continue
            raise RuntimeError(f"网络错误 {url}: {e}")
    raise RuntimeError(f"多次重试失败：{url}")


def count_items(path, params=None):
    """用 per_page=1 + Link 头里的最后一页页码，一次请求拿到列表总数。"""
    p = dict(params or {})
    p["per_page"] = 1
    data, headers = request(path, p)
    link = headers.get("Link") or ""
    m = re.search(r'[?&]page=(\d+)>;\s*rel="last"', link)
    if m:
        return int(m.group(1))
    return len(data) if isinstance(data, list) else 0


def search_count(query):
    time.sleep(SEARCH_PAUSE)
    data, _ = request("/search/issues", {"q": query, "per_page": 1})
    return data["total_count"]


def days_between(iso, now):
    return round((now - datetime.fromisoformat(iso.replace("Z", "+00:00"))).total_seconds() / 86400, 1)


def fetch_repo(full_name, group, now):
    owner = full_name.split("/")[0]
    print(f"→ {full_name}", file=sys.stderr)
    info, _ = request(f"/repos/{full_name}")

    # issue / PR 数量（搜索接口直接给总数，不用翻页）
    q = f"repo:{full_name}"
    issues_open = search_count(f"{q} is:issue is:open")
    issues_closed = search_count(f"{q} is:issue is:closed")
    prs_merged = search_count(f"{q} is:pr is:merged")
    prs_open = search_count(f"{q} is:pr is:open")
    # 外部人提交并被合并的 PR（排除作者本人）
    prs_merged_external = search_count(f"{q} is:pr is:merged -author:{owner}")

    # 贡献者（排除作者本人）
    try:
        contributors_total = count_items(f"/repos/{full_name}/contributors")
        first_page, _ = request(f"/repos/{full_name}/contributors", {"per_page": 100})
        owner_in = any(c.get("login", "").lower() == owner.lower() for c in (first_page or []))
        external_contributors = contributors_total - (1 if owner_in else 0)
    except RuntimeError as e:
        print(f"  贡献者统计失败：{e}", file=sys.stderr)
        contributors_total = external_contributors = None

    since = (now - timedelta(days=90)).strftime("%Y-%m-%dT%H:%M:%SZ")
    commits_90d = count_items(f"/repos/{full_name}/commits", {"since": since})
    releases = count_items(f"/repos/{full_name}/releases")

    stars, forks = info["stargazers_count"], info["forks_count"]
    total_issues = issues_open + issues_closed
    age_days = days_between(info["created_at"], now)

    return {
        "repo": full_name,
        "group": group,
        "language": info.get("language") or "",
        "stars": stars,
        "forks": forks,
        "watchers": info.get("subscribers_count", 0),
        "issues_open": issues_open,
        "issues_closed": issues_closed,
        "prs_merged": prs_merged,
        "prs_open": prs_open,
        "prs_merged_external": prs_merged_external,
        "contributors_total": contributors_total,
        "external_contributors": external_contributors,
        "commits_90d": commits_90d,
        "releases": releases,
        "age_days": age_days,
        "days_since_push": days_between(info["pushed_at"], now),
        # 派生指标
        "fork_rate": round(forks / stars, 4) if stars else 0,
        "issue_close_rate": round(issues_closed / total_issues, 4) if total_issues else 0,
        "stars_per_day": round(stars / age_days, 1) if age_days else 0,
        "archived": info.get("archived", False),
        "created_at": info["created_at"],
    }


def main():
    now = datetime.now(timezone.utc)
    if not TOKEN:
        print("未设置 GITHUB_TOKEN，用匿名额度（每小时 60 次），会比较慢。", file=sys.stderr)

    rows = []
    for name, group in [(r, "target") for r in TARGETS] + [(r, "control") for r in CONTROLS]:
        try:
            rows.append(fetch_repo(name, group, now))
        except RuntimeError as e:
            print(f"  跳过 {name}：{e}", file=sys.stderr)

    if not rows:
        sys.exit("一个仓库都没拉到，检查网络或 Token。")

    with open("metrics.json", "w", encoding="utf-8") as f:
        json.dump({"fetched_at": now.isoformat(), "repos": rows}, f, ensure_ascii=False, indent=2)
    with open("metrics.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    print(f"\n完成：{len(rows)} 个仓库，已写入 metrics.csv / metrics.json（数据时间 {now:%Y-%m-%d %H:%M} UTC）", file=sys.stderr)


if __name__ == "__main__":
    main()
