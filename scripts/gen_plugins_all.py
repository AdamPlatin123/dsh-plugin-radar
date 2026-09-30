#!/usr/bin/env python3
"""gen_plugins_all.py — 兼容壳：转发到 build_canonical + render_all（P1 数据层收敛）。

历史：本文件曾是 408 行的数据+渲染单体（快照装载/canonical 归并/定位复核/登记兜底/
改名跟随/回填重分类 + PLUGINS-ALL.md 与 catalog/all 渲染混在一个 main 里）。
拆分后：
  - 数据半场 → engine/aggregation/build_canonical.py（产 generated/current/canonical.json）
  - 渲染半场 → engine/rendering/render_all.py（PLUGINS-ALL.md + catalog/all/*.md）
本壳保持两个消费方接口不变：
  - main() 返回 {'domains': …, 'global': …}（render-readme-from-snapshot.py 消费）
  - CLI：python3 scripts/gen_plugins_all.py（runner-smoke 冒烟②调用）
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
for p in (ROOT / 'engine' / 'aggregation', ROOT / 'engine' / 'rendering', ROOT / 'scripts'):
    sys.path.insert(0, str(p))

from build_canonical import build  # noqa: E402
from render_all import render      # noqa: E402


def main():
    canonical = build(ROOT)
    return render(canonical)


if __name__ == '__main__':
    main()
