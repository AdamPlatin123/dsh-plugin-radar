#!/usr/bin/env python3
"""classify.py — 分类 v2 规则引擎（taxonomy v2，13 类）。

与 docs/CATALOGING.md 的固定标准同源：每类一组关键词规则（名称/描述正则），
按声明顺序首个命中者胜。用途：
  ① gen_plugins_all 对「❓ 其他」条目做兜底重分类（仅其他类，上游已分类不动）；
  ② bot 提 PR 前的预归类 CLI：python3 scripts/classify.py "<name>" "<desc>"
    输出建议分类与命中规则，作为 PR 分类字段的预填值。
"""
import re
import sys

TAXONOMY_VERSION = 'v2'

DOMAINS = [
    ('🎓 技能包', '以 skill 形态提供能力：技能集合、技能分发、技能搜索'),
    ('🧠 记忆增强', '跨会话/长期记忆、记忆检索与蒸馏：memory、会话历史沉淀、自省与召回'),
    ('🎨 主题皮肤', '外观主题、皮肤、CSS/配色/像素装饰：不改变功能仅改变观感'),
    ('🛒 市场与管理', '插件市场、包管理器、健康检查、装卸载与版本管理工具'),
    ('🔌 Web UI 增强', 'Web/TUI 界面功能增强：侧栏、输入、面板、批注、状态栏、渲染交互'),
    ('💻 编码开发', '编码场景：代码操作、git、diff、终端、语言与构建、测试'),
    ('🤖 Agent 能力', 'agent 本体能力：子代理、规划执行、上下文管理、唤醒睡眠、自主循环'),
    ('📡 消息通讯', 'IM 接入与消息通道：微信/QQ/TG/飞书 bot、消息分享与跨端'),
    ('🗂 文件数据', '文件与数据：读写转换、爬取、数据库、文档解析、知识库'),
    ('🎮 娱乐生活', '摸鱼与趣味：游戏、宠物、表情、音乐、行情、旅行'),
    ('🛠 基建部署', '运行环境与分发：客户端、远程、沙箱、代理、监控、分发渠道'),
    ('📚 学习研究', '学习与探索：教程、指南、评测基准、研究复现'),
    ('❓ 其他', '以上皆不匹配（兜底；提 PR 时请尽量给出更准确的分类）'),
]
RULES = [
    ('🎓 技能包', r'skill|技能'),
    ('🧠 记忆增强', r'\bmem(or(y|ies))?|记忆|recal?l|遗忘|蒸馏|distill'),
    ('🎨 主题皮肤', r'theme|skin|皮肤|主题|像素|壁纸|外观|css|sticker|贴纸|表情包|emoji'),
    ('🛒 市场与管理', r'market|store|registry|manager|插件管理|市场|商店|工坊|workshop|health.?check|健康检查|卸载|installer|包管理|插件浏览'),
    ('🔌 Web UI 增强', r'web\s*ui|webui|sidebar|侧边?栏|侧栏|输入框|input|面板|panel|批注|annotat|状态栏|status.?bar|dock|气泡|toast|导航|navbar|侧面板'),
    ('💻 编码开发', r'code|编码|git\b|github|diff|终端|terminal|shell|lsp|语言|编译|compile|build|测试|test|refactor|lint|debug|审查|review'),
    ('🤖 Agent 能力', r'agent|子代理|subagent|规划|plan|执行|exec|上下文|context|唤醒|睡眠|睡眠|自治|autonom|loop|循环|预算|budget|审批|approv'),
    ('📡 消息通讯', r'微信|wechat|wecom|飞书|feishu|lark|telegram|\btg\b|\bqq\b|机器人|bot|通知|notify|消息|message|群|chat'),
    ('🗂 文件数据', r'文件|file|数据|data|爬|crawl|抓取|数据库|database|sqlite|文档|document|pdf|知识库|kb|rag|索引|index|ocr|表格|excel|csv'),
    ('🎮 娱乐生活', r'游戏|game|宠物|pet|鲸鱼|whale|音乐|music|股票|stock|行情|摸鱼|旅行|travel|小说|漫画|运势|抽奖'),
    ('🛠 基建部署', r'沙箱|sandbox|部署|deploy|远程|remote|ssh|docker|k8s|监控|monitor|分发|distro|发行版|桌面|desktop|托盘|tray|更新|update|代理|proxy|mcp'),
    ('📚 学习研究', r'教程|tutorial|指南|guide|文档导航|评测|benchmark|基准|研究|research|论文|paper|学习|learn'),
]
_RULES = [(dom, re.compile(pat, re.I)) for dom, pat in RULES]


def classify(name: str, desc: str):
    """返回 (建议分类, 命中关键词或 None)。规则按声明顺序首个命中；无命中归「其他」。"""
    text = f'{name} {desc}'
    for dom, rx in _RULES:
        m = rx.search(text)
        if m:
            return dom, m.group(0)
    return '❓ 其他', None


def cli():
    if len(sys.argv) < 2:
        print(__doc__)
        print('用法: python3 scripts/classify.py "<name>" ["<desc>"]')
        print('\ntaxonomy v2 类目:')
        for dom, desc in DOMAINS:
            print(f'  {dom} — {desc[:40]}')
        sys.exit(0)
    name = sys.argv[1]
    desc = sys.argv[2] if len(sys.argv) > 2 else ''
    dom, hit = classify(name, desc)
    print(f'建议分类: {dom}')
    print(f'命中规则: {hit or "（无，兜底为其他）"}')
    definition = next((dd for d, dd in DOMAINS if d == dom), '')
    print(f'类目定义: {definition}')


if __name__ == '__main__':
    cli()
