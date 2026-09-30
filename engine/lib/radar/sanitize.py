#!/usr/bin/env python3
"""sanitize — 第三方可控字段统一消毒（P2b）。

威胁模型：desc/name/url 由插件作者与上游快照控制，渲染链曾零转义——
换行可伪造新条目、方括号可注入钓鱼链接、非白名单 URL 可指向任意站点，
且产物会被 bot 自动合并分发到双仓。接入点单一收口：build_canonical
（render_all 与 export-data 同源消费，一处消毒两条出口全覆盖）。

语义（外科式，非焦土式）：
- md_inline(s)：换行/回车 → 空格（杀条目伪造；当前数据零命中，零漂移）
- md_link_kill(s)：[ ] 反斜杠转义（杀链接注入；实测 16 条 desc 命中，有意变更）
- 竖线与反引号保留：渲染目标为列表行非表格，本就无害；上游部分描述已自带 \\|
- url_guard(u)：GitHub 仓库 URL 白名单；不过 → None（调用方降级为纯文本名）
  （当前数据零违规，零漂移——保护面向未来条目）
"""
import re

_GH_URL = re.compile(r'^https://github\.com/[A-Za-z0-9_.\-]+/[A-Za-z0-9_.\-]+/?$')


def md_inline(s: str) -> str:
    """行内文本消毒：消灭换行类控制符（条目伪造向量）。"""
    return re.sub(r'[\r\n\t]+', ' ', s or '').strip()


def md_link_kill(s: str) -> str:
    """消灭方括号链接语法（钓鱼链接注入向量）；语义保留字符本体。"""
    return (s or '').replace('[', '\\[').replace(']', '\\]')


def sanitize_name(name: str) -> str:
    """展示名：行内消毒 + 去方括号/反引号（名字里不该有 Markdown 结构字符）。"""
    s = md_inline(name)
    return s.replace('[', '').replace(']', '').replace('`', '')


def sanitize_desc(desc: str) -> str:
    """描述：行内消毒 + 链接语法转义（保留字符本体与竖线/反引号）。"""
    return md_link_kill(md_inline(desc))


def url_guard(url: str):
    """GitHub 仓库 URL 白名单；不合规返回 None（调用方降级为纯文本，不呈现链接）。"""
    u = (url or '').strip()
    return u if _GH_URL.match(u) else None
