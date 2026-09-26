#!/usr/bin/env bash
# 生成 README「分类目录」章节——顶层按功能领域分类（非仓库类型）
# 渲染规则：
#   - 顶层 = 功能领域（webui/agent/coding/comm/data/fun/infra/edu/other），每类 <details> 折叠、h3 大标题 + 描述
#   - 每条带类型标签（插件/技能/合集/渠道/基建/研究/社区），来自 catalog 的 category
#   - 每类一次展开全部条目（不分段）「展开全部」
#   - DOMAIN_MAP 全量重分类（268 条，人工审校；P4b 出壳至 data/domain-map.json）；未映射归 other
# 数据源：hub catalog.json（gh api 实时拉取；--offline 或拉取失败时用 data/hub-catalog-cache.json 缓存）
# 渲染由 python3 完成
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"   # engine/rendering → 仓库根
cd "$ROOT" || exit 2
GH="$HOME/.local/bin/gh"
DOMAIN_MAP_JSON="$ROOT/data/domain-map.json"
[ -f "$DOMAIN_MAP_JSON" ] || { echo "[gen-catalog] 缺 $DOMAIN_MAP_JSON，跳过"; exit 0; }

CATALOG="$(mktemp)"
if [ "${1:-}" = "--offline" ] && [ -s "$ROOT/data/hub-catalog-cache.json" ]; then
  cp "$ROOT/data/hub-catalog-cache.json" "$CATALOG"
  echo "[gen-catalog] --offline：使用 hub catalog 缓存 $(wc -c < "$CATALOG") 字节"
else
  timeout 90 "$GH" api "repos/dsh-external/hub/contents/catalog.json" --jq '.content' 2>/dev/null | base64 -d 2>/dev/null > "$CATALOG"
  if [ -s "$CATALOG" ] && [ "${1:-}" = "--cache" ]; then
    cp "$CATALOG" "$ROOT/data/hub-catalog-cache.json"   # 顺手刷新缓存
  fi
fi
if [ ! -s "$CATALOG" ] && [ -s "$ROOT/data/hub-catalog-cache.json" ]; then
  echo "[gen-catalog] hub catalog 拉取失败，回退缓存"
  cp "$ROOT/data/hub-catalog-cache.json" "$CATALOG"
fi
[ -s "$CATALOG" ] || { echo "[gen-catalog] hub catalog 拉取失败且无缓存，跳过"; rm -f "$CATALOG"; exit 0; }

python3 - "$CATALOG" <<'PYEOF'
import json, os, re, sys
ROOT_DIR = os.environ.get("RADAR_ROOT", os.getcwd())
catalog = json.load(open(sys.argv[1], encoding="utf-8"))
DESC_CACHE = {}
if os.path.isfile("data/desc-cache.json"):
    DESC_CACHE = json.load(open("data/desc-cache.json", encoding="utf-8"))
repos = catalog.get("repos", [])

# 领域体系/类型标签/全量映射/补录仓库：统一自 data/domain-map.json（P4b 出壳）
DM = json.load(open(os.path.join(ROOT_DIR, "data", "domain-map.json"), encoding="utf-8"))
DOMAIN_META = [(m["key"], m["title"], m["desc"]) for m in DM["domain_meta"]]
TYPE_LABEL = DM["type_label"]
DOMAIN_MAP = DM["domain_map"]
EXTRA_REPOS = {k: (v["url"], v["desc"], v["domain"]) for k, v in DM["extra_repos"].items()}



# 从最新 mainline-compat.md 读取兼容性判定
import glob, os
VERDICT_MAP = {}
_reports = sorted(glob.glob('reports/20*/'))
if _reports:
    _compat = os.path.join(_reports[-1], 'mainline-compat.md')
    if os.path.isfile(_compat):
        for _line in open(_compat, encoding='utf-8'):
            _m = re.match(r'^\|\s*([A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)?)\s*\|.*\|\s*([^|]+?)\s*\|$', _line)
            if _m:
                VERDICT_MAP[_m.group(1)] = _m.group(2).strip()

VERDICT_RANK = {'兼容': 0, '关注': 1, '需适配': 2, '待调研': 3, '占位': 4, '不适用': 5, '已删除': 6}

def verdict_label(repo):
    v = VERDICT_MAP.get(repo.get('name', ''), '待调研')
    for k in VERDICT_RANK:
        if k in v:
            return k
    return '待调研'

def verdict_key(repo):
    return VERDICT_RANK.get(verdict_label(repo), 3)

def short_desc(repo):
    name = repo.get("name", "")
    d = DESC_CACHE.get(name, "")
    if not d:
        d = repo.get("description") or ""
    if d == "null" or not d.strip():
        return "—"
    d = d.split("。")[0].strip()
    if not d:
        d = d.split(".")[0].strip()
    return d[:80] if d else "—"


groups = {key: [] for key, _, _ in DOMAIN_META}
# 合并 catalog 与 EXTRA_REPOS（PR 登记新插件）
merged_repos = list(repos)
for name, (url, desc, domain) in EXTRA_REPOS.items():
    merged_repos.append({"name": name, "url": url, "description": desc, "category": "plugin"})
for r in merged_repos:
    domain = DOMAIN_MAP.get(r.get("name", ""), "other")
    if r.get("name") in EXTRA_REPOS:
        domain = EXTRA_REPOS[r["name"]][2]
    groups.setdefault(domain, []).append(r)
# 每个领域内按兼容性排序（兼容在前）
for k in groups:
    groups[k] = sorted(groups[k], key=verdict_key)

out = []
out.append("<!-- AUTO:catalog:START -->")
out.append("")
out.append("> 按功能领域分类（重分类修正）。点击标题展开，全部条目一次显示。")
out.append("")
for key, title, desc in DOMAIN_META:
    items = groups.get(key, [])
    n = len(items)
    out.append("<details>")
    out.append(f"<summary><h3>{title}（{n}）</h3></summary>")
    out.append("")
    out.append(f"*{desc}*")
    out.append("")
    out.append("| 插件 | 类型 | 兼容性 | 说明 |")
    out.append("|---|---|---|---|")
    if n == 0:
        out.append("| （暂无） | — | — |")
    else:
        for r in items:
            t = TYPE_LABEL.get(r.get("category", ""), "插件")
            _v = verdict_label(r)
            out.append(f"| [{r['name']}]({r.get('url', '')}) | {t} | {_v} | {short_desc(r)} |")
    out.append("</details>")
    out.append("")
    # 描述第二遍：块外持续显示（默认可见，不随折叠消失）
    out.append(f"*{desc}*")
    out.append("")
out.append("<!-- AUTO:catalog:END -->")

block = "\n".join(out)
p = "README.md"
s = open(p, encoding="utf-8").read()
start = "<!-- AUTO:catalog:START -->"
end = "<!-- AUTO:catalog:END -->"
if start in s:
    i = s.index(start)
    j = s.index(end) + len(end)
    s = s[:i] + block + s[j:]
else:
    anchor = "## 当前生态快照"
    i = s.index(anchor)
    s = s[:i] + "## 分类目录\n\n" + block + "\n" + s[i:]
open(p, "w", encoding="utf-8").write(s)
print("CATALOG_BLOCK_UPDATED")
PYEOF
rm -f "$CATALOG"
exit 0
