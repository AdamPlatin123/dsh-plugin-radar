#!/usr/bin/env python3
"""gen-pipeline-diagram.py v2 — 工作原理图生成器：脚本常量（拓扑）+ 指标流（活数字）。

拓扑参数读自各脚本常量；计数读 ~/dsh-k8s/metrics/*.jsonl 流头（60s 采样）。
流缺失 → 该数字显示 —（fail-safe，绝不拿旧数冒充）。
产物注入 README 的 AUTO:pipeline:START/END 块。语法固定 flowchart + 全引号节点。
"""
import json
import re
import sys
from datetime import datetime
from pathlib import Path

HOME = Path.home()
FRONT = HOME / "dsh-external-research"
MET = HOME / "dsh-k8s/metrics"

def facts():
    f = {"topic_n": 2, "kw_n": 3, "spacing": 35, "cap": 10, "batch": 100,
         "probe": "*/15", "streams": 7, "stream_sec": 60, "discover_hours": 6}
    try:
        s = (FRONT / "engine/discovery/discover.py").read_text()
        f["topic_n"] = s.count('("topic",')
        f["kw_n"] = s.count('("keyword",')
        m = re.search(r"time\.sleep\((\d+)\)", s)
        if m:
            f["spacing"] = int(m.group(1))
    except Exception:
        pass
    try:
        s = (HOME / "dsh-k8s/pipeline-driver.sh").read_text()
        m = re.search(r"CAP=(\d+)", s)
        if m:
            f["cap"] = int(m.group(1))
    except Exception:
        pass
    try:
        s = (HOME / "dsh-k8s/cadence.py").read_text()
        m = re.search(r"BATCH\s*=\s*(\d+)", s)
        if m:
            f["batch"] = int(m.group(1))
    except Exception:
        pass
    return f

def stream(name):
    p = MET / f"{name}.jsonl"
    if not p.exists():
        return {}
    last = None
    for line in p.read_text(errors="ignore").splitlines()[-40:]:
        line = line.strip()
        if line:
            try:
                last = json.loads(line)
            except json.JSONDecodeError:
                continue
    return last or {}

def live():
    d, c, t, v, dl = (stream(n) for n in ("discover", "clone", "test", "verdict", "deliver"))
    fmt = lambda x: "—" if x is None else str(x)
    return {
        "cand": fmt(d.get("candidates")), "age": fmt(d.get("age_min")),
        "plugins": fmt(c.get("plugins")), "nonplugin": fmt(c.get("nonplugin")),
        "clones": fmt(c.get("clones")),
        "running": fmt(t.get("running")), "done": fmt(t.get("succeeded")),
        "pass": fmt(v.get("pass")), "fail": fmt(v.get("fail")),
        "inc": fmt(v.get("inc")), "total": fmt(v.get("total")),
        "delta": fmt(dl.get("delta_since")),
    }

TEMPLATE = """```mermaid
flowchart TB
    subgraph Discovery["🔍 发现（每 {discover_hours} 小时 · probe {probe} 巡检触发）"]
        A1["GitHub Search<br/>topic ×{topic_n} + keyword ×{kw_n}<br/>候选 {cand} · 龄 {age}m"]
        A2["本地库补全 · 去重 repo id"]
        A3["🚫 私有 org 仓排除<br/>{spacing}s 错峰 · 403 退避 · dshow 黑名单"]
    end
    subgraph Validation["📋 验证（driver 20s 流式循环）"]
        B1{{"package.json<br/>name + main/exports/dsh?"}}
    end
    B1 -->|"插件 {plugins}"| C1["k8s 运行级测试<br/>一插件一 pod · 并发 {cap}<br/>dsh agent + Qwen（de-stream）"]
    B1 -->|"非插件（累计删 {nonplugin}）"| B3["❌ 即删省空间"]
    C1 --> D1{{"判定 · 总 {total}"}}
    D1 -->|"✅ {pass} / ❌ {fail}"| E1["聚合 + README 分类统计"]
    D1 -->|"⚠️ {inc} 环境类重试"| C1
    E1 --> E2["cadence 交付<br/>本周期增量 {delta}/{batch}<br/>双仓 bot PR（幂等 supersede）"]
    S["⚖️ 静态四维轨（每日 02:00）"] -.-> E1
    M["🛡 radar-probe {probe} 自愈<br/>{streams} 指标流 × {stream_sec}s · 完成累计 {done}"] -.-> A1
    M -.-> C1
```"""

def render(f, l):
    merged = {**f, **l}
    t = TEMPLATE.format(**merged)
    return t.replace("{{", "{").replace("}}", "}")

def refresh_badges(readme: Path, l):
    """三枚徽章刷新：confirmed=插件数 · tested=判定总数 · scan=发现节奏（小时）。"""
    t = readme.read_text()
    t = re.sub(r"badge/confirmed-\d+", f"badge/confirmed-{l['plugins']}", t)
    t = re.sub(r"badge/tested-\d+", f"badge/tested-{l['total']}", t)
    readme.write_text(t)


def inject(readme: Path, block: str):
    t = readme.read_text()
    a, b = "<!-- AUTO:pipeline:START -->", "<!-- AUTO:pipeline:END -->"
    wrapped = a + "\n" + block + "\n" + b
    if a in t and b in t:
        i, j = t.find(a), t.find(b) + len(b)
        t = t[:i] + wrapped + t[j:]
    else:
        m = re.search(r"```mermaid\s*\n.*?```", t, re.S)
        assert m, "未找到 mermaid 块"
        t = t.replace(m.group(0), wrapped, 1)
    readme.write_text(t)

if __name__ == "__main__":
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("README.md")
    f, l = facts(), live()
    inject(target, render(f, l))
    refresh_badges(target, l)
    print(f"[gen-diagram] {target} · 拓扑: topic×{f['topic_n']} kw×{f['kw_n']} CAP={f['cap']} batch={f['batch']} · 活数字: 候选{l['cand']} 插件{l['plugins']} 判定{l['total']}({l['pass']}✅/{l['fail']}❌/{l['inc']}⚠️) 增量{l['delta']}/{f['batch']}")
