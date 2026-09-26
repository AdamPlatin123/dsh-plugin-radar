#!/usr/bin/env python3
"""thresholds — 缩水保护阈值唯一来源（P3；此前两套阈值分散两处无对照）。

两档语义刻意不同，勿合并：
- DISCOVER_PARTIAL_RATIO：发现层候选总量较上轮跌破该比例 → 写 partial 文件
  保全旧版、退出 25（保守止血——可能只是 GitHub 搜索抖动，旧版继续可用）；
- AGGREGATE_SHRINK_RATIO：聚合层候选总量较上轮低于该比例 → fail-closed 退出 20
  （硬失败——数据面疑似丢源，宁停勿坏）。
"""
DISCOVER_PARTIAL_RATIO = 0.6   # engine/discovery/discover.py（历史值，2026-08 起生效）
AGGREGATE_SHRINK_RATIO = 0.95  # engine/aggregation/aggregate.py（SOP §8.1）
