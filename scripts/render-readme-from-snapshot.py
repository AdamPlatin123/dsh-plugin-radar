#!/usr/bin/env python3
"""render-readme-from-snapshot.py — Bot B：从已合并快照渲染 README（仓库内运行，零外部依赖）。

契约：只读 data/snapshots/*.json（取 run_id 最新），绝不访问网络/指标流。
渲染面（中英两版 README 同步渲染；语言专属正则不命中即安全跳过）：
  三徽章 + 证据层运行级行 + AUTO:pipeline 活数字图（中文版）+ 「数据截至」锚（中文版）
  + 头部数字面 + 目录对账 + 生态快照块头行/报告链接。
时间戳统一输出北京时间（UTC+8）。
幂等：同快照重复渲染输出逐字节一致。
"""
import json
import re
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SNAP_DIR = ROOT / "data" / "snapshots"

DIAGRAM = """```mermaid
flowchart TB
    subgraph Discovery["发现（每 {discover_hours} 小时 · probe {probe} 巡检触发）"]
        A1["GitHub Search<br/>topic ×{topic_n} + keyword ×{kw_n}<br/>候选 {cand} · 龄 {age}m"]
        A2["本地库补全 · 去重 repo id"]
        A3["私有 org 仓排除<br/>{spacing}s 错峰 · 403 退避 · dshow 黑名单"]
    end
    subgraph Validation["验证（driver 20s 流式循环）"]
        B1{{"package.json<br/>name + main/exports/dsh?"}}
    end
    B1 -->|"插件 {plugins}"| C1["k8s 运行级测试<br/>一插件一 pod · 并发 {cap}<br/>dsh agent + Qwen（de-stream）"]
    B1 -->|"非插件（累计删 {nonplugin}）"| B3["即删省空间"]
    C1 --> D1{{"判定 · 总 {total}"}}
    D1 -->|"{pass} / {fail}"| E1["聚合 + README 分类统计"]
    D1 -->|"{inc} 环境类重试"| C1
    E1 --> E2["cadence 交付<br/>本周期增量 {delta}/{batch}<br/>双仓 bot PR（幂等 supersede）"]
    M["radar-probe {probe} 自愈<br/>{streams} 指标流 × {stream_sec}s · 完成累计 {done}"]
    M -.-> A1
    M -.-> C1
```"""


DIAGRAM_EN = """```mermaid
flowchart TB
    subgraph Discovery["Discovery (every {discover_hours}h · probe {probe})"]
        A1["GitHub Search<br/>topic ×{topic_n} + keyword ×{kw_n}<br/>candidates {cand} · age {age}m"]
        A2["Local DB merge · dedupe by repo id"]
        A3["Private org repos excluded<br/>{spacing}s stagger · 403 backoff · dshow blocklist"]
    end
    subgraph Validation["Validation (driver 20s streaming loop)"]
        B1{{"package.json<br/>name + main/exports/dsh?"}}
    end
    B1 -->|"plugins {plugins}"| C1["k8s runtime test<br/>1 pod per plugin · concurrency {cap}<br/>dsh agent + Qwen (de-stream)"]
    B1 -->|"non-plugins (dropped {nonplugin})"| B3["dropped to save space"]
    C1 --> D1{{"verdict · total {total}"}}
    D1 -->|"{pass} / {fail}"| E1["aggregate + README stats"]
    D1 -->|"{inc} env retries"| C1
    E1 --> E2["cadence deliver<br/>delta this cycle {delta}/{batch}<br/>dual-repo bot PRs (idempotent)"]
    M["radar-probe {probe} self-heal<br/>{streams} metric streams × {stream_sec}s · done {done}"]
    M -.-> A1
    M -.-> C1
```"""

def latest_snapshot():
    if not SNAP_DIR.exists():
        return None
    snaps = sorted(SNAP_DIR.glob("*.json"))
    for p in reversed(snaps):
        try:
            return json.loads(p.read_text())
        except json.JSONDecodeError:
            continue
    return None


def bj(iso_str, fmt="%Y-%m-%d %H:%M:%S"):
    """ISO 时间串 → 北京时间显示（UTC+8）；带时区偏移按原偏移换算，避免二次加 8；解析失败原样返回。"""
    try:
        dt = datetime.fromisoformat(str(iso_str).replace("Z", "+00:00"))
    except ValueError:
        return str(iso_str)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone(timedelta(hours=8))).strftime(fmt) + " UTC+8"


def fmt(x):
    return "—" if x is None else str(x)


def main():
    snap = latest_snapshot()
    if (not isinstance(snap, dict)
            or snap.get("schema") not in ("radar-snapshot/1", "radar-snapshot/2")
            or any(not isinstance(snap.get(k), dict)
                   for k in ("verdict", "discovery", "clone", "test", "deliver"))
            or not isinstance(snap.get("run_id"), str) or not snap["run_id"]
            or not isinstance(snap.get("generated_at"), str) or not snap["generated_at"]):
        # 安全停旧 = 不写任何产物并显式非零退出（曾打印后继续索引 snap → NoneType/KeyError 崩栈）
        print("[render] 无有效快照（radar-snapshot/*）— 保持 README 现状（安全停旧）")
        return 1

    v, d, c, t, dl = (snap[k] for k in ("verdict", "discovery", "clone", "test", "deliver"))
    topo = snap.get("topology", {})

    # ⓪ 全量清单随每轮快照重生成（PLUGINS-ALL.md），并取九类分布供目录摘要卡使用；
    #    global.un = 登记兜底口径的未测数（快照 catalog 不产 ⏳，磁贴未测恒 0 的修复数据源）
    g_un = None
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from gen_plugins_all import main as gen_all
        stats = gen_all() or {}
        domain_stats = stats.get('domains') or stats   # 兼容旧返回结构（裸 dict）
        g_un = (stats.get('global') or {}).get('un')
    except Exception as _e:
        print(f"[render] WARN 清单生成跳过: {_e}")
        domain_stats = {}
    # 2026-09-16 双语合并：README 单文件化（中文行+英文行交错），en-US 转存根
    for path in (ROOT / "README.md",):
        is_zh = True
        t_readme = path.read_text()


        # ⓪ 去重自愈：徽章行与三色磁贴行历史曾叠出双份（数字不同轮互相打架）——
        #    渲染前收敛为单份（徽章行保留首行；中文磁贴保留最后一组=最新插入；英文行同理）
        def _dedup_lines(t, pattern, keep='first'):
            lines = t.split('\n')
            idx = [i for i, l in enumerate(lines) if re.match(pattern, l)]
            if len(idx) > 1:
                drop = idx[1:] if keep == 'first' else idx[:-1]
                for i in reversed(drop):
                    del lines[i]
                t = '\n'.join(lines)
            return t
        t_readme = _dedup_lines(t_readme, r'^\[!\[confirmed\].*$')
        t_readme = _dedup_lines(t_readme, r'^\[!\[运行级可用\].*$', keep='last')
        t_readme = _dedup_lines(t_readme, r'^\[!\[runtime OK\].*$', keep='last')

        # ① 三徽章（两版通用）
        t_readme = re.sub(r"badge/confirmed-\d+", f"badge/confirmed-{fmt(c.get('plugins'))}", t_readme)
        t_readme = re.sub(r"badge/tested-\d+", f"badge/tested-{fmt(v.get('total'))}", t_readme)

        # ①b 三色磁贴（整行重建）：绿=可用 红→黄=需适配（原「不兼容」） 灰=待测（待定+未测）；
        #     左半「档名 数量」，右半 = runner 镜像版本（快照 verdict.cur_image，与 results 的
        #     runner_image_digest 同源统一；shields 徽章 message 中的 '-' 按惯例转义 '--'）
        vcnt = Counter(e.get("verdict", "") for e in (snap.get("catalog_entries") or []))
        n_ok = vcnt.get("✅ 运行级可用", 0) or vcnt.get("运行级可用", 0)
        n_bad = vcnt.get("❌ 运行级不兼容", 0) or vcnt.get("运行级不兼容", 0)
        n_inc = vcnt.get("⚠️ 待定", 0) or vcnt.get("待定", 0)
        n_un = g_un if isinstance(g_un, int) else vcnt.get("⏳ 未测", 0)
        img = str(v.get("cur_image", "") or "").strip()
        try:  # 版本对齐：优先 runner 实测多版本中的最新（results.runner_image_digest 聚合）
            import json as _j
            _rv = _j.loads((ROOT / "data" / "runner-versions.json").read_text())
            img = f"dsh-test-runner:{_rv.get('latest') or img}" if _rv.get('latest') else img
        except Exception:
            pass
        ver = (img.split(":", 1)[1] if ":" in img else img).replace("-", "--")
        n_test = n_inc + n_un

        def _badge(label, count, color, ver_str):
            msg = f"{label}_{count}-{ver_str}" if ver_str else f"{label}-{count}"
            return f"https://img.shields.io/badge/{msg}-{color}"

        # 按版本分离的判定表（替代混合磁贴——用户需求：多主线版本各自独立呈现）
        #     数据源 runner-versions.json（逐条 runner_image_digest 聚合），每版本独立计数
        try:
            _rvd2 = _j.loads((ROOT / "data" / "runner-versions.json").read_text()) if '_j' in dir() else {}
        except Exception:
            _rvd2 = {}
        _lt2 = _rvd2.get("latest") or ""
        def _vk2(t):
            m2 = re.match(r"(\d+)\.(\d+)\.(\d+)-rc\.(\d+)$", t)
            return (int(m2.group(1)), int(m2.group(2)), int(m2.group(3)), int(m2.group(4))) if m2 else (0, 0, 0, 0)
        _vs2 = sorted(_rvd2.get("versions", {}).items(), key=lambda kv: (kv[0] == _lt2, _vk2(kv[0])), reverse=True)
        _vrows = []
        for _t2, _c2 in _vs2:
            if sum(_c2.values()) < 5:
                continue  # 孤儿版本（<5 条）过滤——如 digest 标签为 latest 的历史残留
            _ok2 = _c2.get("ok", 0); _bad2 = _c2.get("fail", 0); _inc2 = _c2.get("inc", 0) + _c2.get("untested", 0)
            _tag2 = f"**{_t2}**（最新 / latest）" if _t2 == _lt2 else _t2
            _vrows.append(f"| {_tag2} | {_ok2} | {_bad2} | {_inc2} | {_ok2 + _bad2 + _inc2} |")
        _vtable = ("**判定按 runner 版本分离 / verdicts by runner version：**\n\n"
                   "| runner 版本 / version | 可用 / OK | 需适配 / adapt | 在测 / testing | 小计 / total |\n"
                   "|---|---:|---:|---:|---:|\n" + "\n".join(_vrows) + "\n"
                   f"| **累计 / cumulative** | **{n_ok}** | **{n_bad}** | **{n_test}** | **{n_ok + n_bad + n_test}** |")
        # 幂等重建：先删旧表格（若有），再替换旧磁贴行（若有）——两者取其一即可；
        # 尾部 \n* 消费旧表后的全部连续空行（\n? 每轮遗留一个空行，重复渲染逐轮累积）
        t_readme = re.sub(r"\*\*判定按 runner 版本分离[\s\S]*?\| \*\*累计 / cumulative\*\*[^\n]*\n*", "", t_readme, count=1)
        t_readme = re.sub(r"^\[!\[运行级可用\][^\n]*\n(?:^$\n)?(?:^\[!\[runtime OK\][^\n]*\n)?(?:^$\n)?",
                          _vtable + "\n\n", t_readme, count=1, flags=re.M)
        # 双保险：若旧磁贴与旧表格都已被清但表格未插入（首次迁移），在 confirmed 徽章行后插入
        if '判定按 runner 版本分离' not in t_readme:
            t_readme = re.sub(r"(^\[!\[confirmed\][^\n]*\n)", r"\1\n" + _vtable.replace("\\", "\\\\") + "\n\n", t_readme, count=1, flags=re.M)
        t_readme = re.sub(r"(（当前 `)[0-9A-Za-z]+(`)", rf"\g<1>{snap['run_id']}\g<2>", t_readme, count=1)
        t_readme = re.sub(r"(currently `)[0-9A-Za-z]+(`)", rf"\g<1>{snap['run_id']}\g<2>", t_readme, count=1)

        # ② 证据层运行级行（整行替换；两版该表均为中文）
        t_readme = re.sub(
            r"^\| 运行级实测 .*$",
            f"| 运行级实测 | {v.get('pass')} 可用 · {v.get('fail')} 不兼容 · {v.get('inc')} 待定"
            f"（共 {v.get('total')} 个，k8s agent 口径）|",
            t_readme, count=1, flags=re.M)
        # ③ AUTO:pipeline 活数字图（中文版专属块；英文版无该标记，自动跳过）
        params = {
            "discover_hours": topo.get("discover_hours", 6),
            "probe": ("每 15 分钟" if is_zh else "every 15 min") if "*/" in str(topo.get("probe", "")) else topo.get("probe", "每 15 分钟" if is_zh else "every 15 min"),
            "topic_n": topo.get("topic_n", 2), "kw_n": topo.get("kw_n", 3),
            "cand": fmt(d.get("candidates")), "age": fmt(d.get("age_min")),
            "plugins": fmt(c.get("plugins")), "nonplugin": fmt(c.get("nonplugin")),
            "cap": topo.get("cap", 10), "total": fmt(v.get("total")),
            "pass": fmt(v.get("pass")), "fail": fmt(v.get("fail")), "inc": fmt(v.get("inc")),
            "delta": fmt(dl.get("delta_since")), "batch": topo.get("batch", 100),
            "streams": topo.get("streams", 7), "stream_sec": topo.get("stream_sec", 60),
            "done": fmt(t.get("succeeded")),
            "spacing": topo.get("spacing", 35),
        }
        tmpl = DIAGRAM if is_zh else DIAGRAM_EN
        block = tmpl.format(**params).replace("{{", "{").replace("}}", "}")
        a, b = "<!-- AUTO:pipeline:START -->", "<!-- AUTO:pipeline:END -->"
        if a in t_readme and b in t_readme:
            i, j = t_readme.find(a), t_readme.find(b) + len(b)
            seg = t_readme[i:j]
            if '<img src="assets/pipeline-diagram' in seg:
                # 骨架版（mermaid 主显示或 SVG 主显示均适用）：仅替换围栏内活数字源码
                seg2, n = re.subn(r"```(?:mermaid)?\n[\s\S]*?\n```", block, seg, count=1)
                t_readme = t_readme[:i] + (seg2 if n else seg) + t_readme[j:]
            else:
                t_readme = t_readme[:i] + a + "\n" + block + "\n" + b + t_readme[j:]

        # ④ 数据截至锚（中英双版同步维护；对应标题不存在的版本正则不命中、安全跳过）
        anchor_line = f"> 数据截至快照 `{snap['run_id']}`（{bj(snap.get('generated_at', ''))} · 分类器 {snap.get('classifier', '')}）"
        anchor_en = f"> Data as of snapshot `{snap['run_id']}` ({bj(snap.get('generated_at', ''))} · classifier {snap.get('classifier', '')})"
        # 双语布局：标题后紧跟英文副行（无空行），锚对（中+英）整体重写
        t_readme = re.sub(r">\s*数据截至快照 `[^\n]*\n+", "", t_readme)
        t_readme = re.sub(r">\s*[\* ]*Data as of snapshot[^\n]*\n+", "", t_readme)
        anchor_pair = (anchor_line + "\n"
                       f"> *Data as of snapshot — currently `{snap['run_id']}` "
                       f"({bj(snap.get('generated_at', ''))} · classifier {snap.get('classifier', '')})*")
        t_readme = re.sub(r"(## 工作原理\n)", lambda m: m.group(1) + anchor_pair + "\n", t_readme, count=1)

        # ④b 开头数字面（中文文案；英文头部走 EN 专属正则）
        cand_n = d.get("candidates") or 0
        slogan_n = (int(cand_n) // 100) * 100 if cand_n else None
        if slogan_n:
            # 口号与正文导语句共用动态候选数（百位取整 + 号后缀，README 全覆盖轮）
            t_readme = re.sub(r"(自动发现 )\d+\+?( 候选)", rf"\g<1>{slogan_n}+\g<2>", t_readme)
            t_readme = re.sub(r"(发现 )\d+\+?( 候选)", rf"\g<1>{slogan_n}+\g<2>", t_readme, count=1)
        if c.get("plugins"):
            # 四段式递进口径（ADR-0003 展示层）：索引 → 克隆验证 → 清单呈现 → 当前版本实测
            _all_n = sum(int(s.get("total", 0)) for s in domain_stats.values()) if domain_stats else c['plugins']
            _cur = v.get("cur_tested") or 0
            _img = (v.get("cur_image") or "").rsplit(":", 1)[-1] or "current"
            _trio = f"已索引 {cand_n} repos · 克隆验证为 DSH 插件 {c['plugins']} · 清单呈现 {_all_n} · 当前版本 {_img} 实测 {_cur} 个 DSH 插件仓库"
            t_readme = re.sub(r"^> 收录 [^\n]*$", f"> {_trio}", t_readme, count=1, flags=re.M)
            t_readme = re.sub(r"(索引到)\d+( ?个? ?repos)", rf"\g<1>{cand_n}\g<2>", t_readme, count=1)
            t_readme = re.sub(r"(索引到)\d+( ?个? ?repos)", rf"\g<1>{cand_n}\g<2>", t_readme, count=1)
            t_readme = re.sub(r"^\| 自动收录 \| \d+ 个仓库 \|$", f"| 自动收录 | {c['plugins']} 个仓库 |",
                              t_readme, count=1, flags=re.M)
        dh = topo.get("discover_hours", 6)
        t_readme = re.sub(r"badge/scan-every_\d+h", f"badge/scan-every_{dh}h", t_readme, count=1)
        t_readme = re.sub(
            r"\*\*\d+ plugin repos indexed\*\*[^\n]*",
            f"**{fmt(c.get('plugins'))} plugin repos indexed** (manifest-level classification, v2 engine), "
            f"**{fmt(v.get('total'))} runtime-tested on the k8s track**.", t_readme, count=1)

        # ④c 目录对账：快照携带全量条目 → 补缺行 + 坍缩计数单值
        try:
            sys.path.insert(0, str(Path(__file__).resolve().parent))
            from reconcile_catalog import reconcile_catalog
            t_readme = reconcile_catalog(t_readme, snap.get("catalog_entries") or [])
        except Exception as _e:
            print(f"[render] WARN 目录对账跳过: {_e}")

        # ④d 生态快照块：头行时间戳 / 静态轨行 / 跟踪 PR / 报告链接（两版块内均中文）
        try:
            _rvd = _j.loads((ROOT / "data" / "runner-versions.json").read_text()) if '_j' in dir() else {}
        except Exception:
            _rvd = {}
        def _vk(t):
            m = re.match(r"(\d+)\.(\d+)\.(\d+)-rc\.(\d+)$", t)
            return (int(m.group(1)), int(m.group(2)), int(m.group(3)), int(m.group(4))) if m else (0, 0, 0, 0)
        _vt = _rvd.get("latest") or ""
        _vd = " · ".join(f"{t} ({sum(c.values())})" for t, c in sorted(_rvd.get("versions", {}).items(),
                      key=lambda kv: (kv[0] == _vt, _vk(kv[0])), reverse=True)[:6])
        t_readme = re.sub(r"^> 按版本分解[^\n]*\n*", "", t_readme, flags=re.M)
        t_readme = re.sub(r"(渲染于快照 [0-9A-Za-z]+（[^\n]*）)",
                          f"\\g<0>\n> 按版本分解 / by runner version：{_vd}" if _vd else "\\g<0>", t_readme, count=1)
        t_readme = re.sub(r"(更新于 [0-9-]+ [0-9:]+[^\n]*|渲染于快照 [0-9A-Za-z]+（[^\n]*）)",
                          f"渲染于快照 {snap['run_id']}（{bj(snap['generated_at'], '%Y-%m-%d %H:%M')}）· 数据源 data/snapshots/（渲染即对齐）",
                          t_readme, count=1)
        rd = sorted([x.name for x in (ROOT / "reports").iterdir() if x.is_dir() and x.name[:2] == "20"]) \
            if (ROOT / "reports").exists() else []
        if rd:
            d_latest = rd[-1]
            # 证据链只链现存资源：静态轨产物（index/mainline-compat/compile-compat）已随资产分离移除；
            # 运行实测指向当日实际存在的 agent-test*.md（bot 交付名为 agent-test-v2.md）
            agent = next((p.name for p in sorted((ROOT / "reports" / d_latest).glob("agent-test*.md"), reverse=True)), None)
            chain = ["[完整索引](PLUGINS-ALL.md)"]
            if agent:
                chain.append(f"[运行实测](reports/{d_latest}/{agent})")
            t_readme = re.sub(r"^\[完整索引\].*$", " · ".join(chain), t_readme, count=1, flags=re.M)

        def gh_slug(text):
            """GitHub 标题锚点：剥离 emoji/标点（保留其占位空格转连字符），对齐 github-slugger。"""
            t = re.sub(r'[^\w\u4e00-\u9fff\-\s]', '', str(text)).lower().lstrip('-')
            return re.sub(r'\s+', '-', t)

        # ④f 分类目录摘要卡：AUTO:catalog 整块重建为九类摘要列表（明细在 PLUGINS-ALL.md，根治大表格挤压）
        if domain_stats:
            if is_zh:
                cards = ["逐插件明细（判定 · 定位 · 星标）按域分页见 **[PLUGINS-ALL.md](PLUGINS-ALL.md)** 索引。", ""]
                for dom, s in domain_stats.items():
                    if not s["total"]:
                        continue
                    dom_path = f"catalog/all/{dom.split(' ', 1)[-1]}.md".replace(" ", "%20")
                    cards.append(f'- **{dom}**（{s["total"]}）— 可用 {s["ok"]} · 不兼容 {s["bad"]} · '
                                 f'待定 {s["inc"]} · 未测 {s["un"]} · 监测 {s["watch"]} — [明细]({dom_path})')
            else:
                cards = ["Per-plugin details (verdict · location · stars) paginated per domain — index in **PLUGINS-ALL.md**.", ""]
                for dom, s in domain_stats.items():
                    if not s["total"]:
                        continue
                    dom_path = f"catalog/all/{dom.split(' ', 1)[-1]}.md".replace(" ", "%20")
                    cards.append(f'- **{dom}**（{s["total"]}）— OK {s["ok"]} · incompatible {s["bad"]} · '
                                 f'pending {s["inc"]} · untested {s["un"]} · watching {s["watch"]} — [details]({dom_path})')
            block = "<!-- AUTO:catalog:START -->\n\n" + "\n".join(cards) + "\n\n<!-- AUTO:catalog:END -->"
            t_readme = re.sub(r"<!-- AUTO:catalog:START -->[\s\S]*?<!-- AUTO:catalog:END -->",
                              lambda _: block, t_readme, count=1)

        path.write_text(t_readme)

    # ⑤ CHANGELOG 运行级条目（快照模式下的唯一写入者；按 run_id 幂等；两文件渲染后单次执行）
    cl = ROOT / "CHANGELOG.md"
    if cl.exists():
        ct = cl.read_text()
        entry_tag = f"<!-- snapshot:{snap['run_id']} -->"
        if entry_tag not in ct:
            entry = (f"## {bj(snap['generated_at'], '%Y-%m-%d')}（运行级 · {snap['run_id']}）{entry_tag}\n"
                     f"- 运行级实测：总 {v.get('total')}：可用 {v.get('pass')} / 真不兼容 {v.get('fail')} / "
                     f"待定 {v.get('inc')}（k8s agent · 公有生态口径）\n"
                     f"- 快照：data/snapshots/{snap['run_id']}.json（本条目与其同源）\n\n")
            ct = re.sub(r"<!-- snapshot:[^>]+>\n## [^\n]*\n(?:- [^\n]*\n){2}\n?", "", ct)
            i2 = ct.find("## ")
            cl.write_text(ct[:i2] + entry + ct[i2:] if i2 >= 0 else entry + ct)

    print(f"[render] run_id={snap['run_id']} · 徽章 confirmed-{c.get('plugins')}/tested-{v.get('total')} · "
          f"判定 {v.get('pass')}/{v.get('fail')}/{v.get('inc')} · 双文件渲染完成")
    return 0


if __name__ == "__main__":
    sys.exit(main())
