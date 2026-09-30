#!/usr/bin/env python3
"""secretsource — 密钥解析唯一实现（P2b；此前三处逐字复制的 sqlite 直读收敛于此）。

解析链（先到先得）：
  1. 环境变量（deepseek → DEEPSEEK_API_KEY，通用 → <NAME大写>_API_KEY）
  2. ~/.radar-keys/<name>（0600 权限的文本文件，首行即密钥——服务器迁移推荐形态）
  3. sqlite 兜底（RADAR_LEGACY_KEY_DB 或 ~/.omp/agent/agent.db 的 auth_credentials 表）

使用纪律（防 argv/ps 暴露）：
  - header 子命令输出 "Authorization: Bearer <key>" 到 stdout，shell 侧重定向进
    0600 临时文件后以 curl -H @file 传递——密钥永不进命令行参数
  - print 子命令仅供过渡期兼容（等价于被替换的旧内联提取），新代码一律 header

CLI：
  python3 secretsource.py deepseek header   # 供 curl -H @file
  python3 secretsource.py deepseek print    # 输出裸密钥（过渡期）
  python3 secretsource.py deepseek probe    # 来源探测，不输出密钥
"""
import json
import os
import sqlite3
import stat
import sys
from pathlib import Path

KEYS_DIR = Path.home() / '.radar-keys'
ENV_MAP = {'deepseek': 'DEEPSEEK_API_KEY'}


def _from_env(name: str):
    var = ENV_MAP.get(name) or f"{name.upper().replace('-', '_')}_API_KEY"
    return os.environ.get(var) or None


def _from_keyfile(name: str):
    p = KEYS_DIR / name
    if not p.is_file():
        return None
    if p.stat().st_mode & 0o077:
        print(f'[secretsource] {p} 权限过宽（应 0600），拒绝读取', file=sys.stderr)
        return None
    first = p.read_text(encoding='utf8').splitlines()
    return first[0].strip() if first else None


def _from_sqlite(name: str):
    db_path = os.environ.get('RADAR_LEGACY_KEY_DB') or str(Path.home() / '.omp' / 'agent' / 'agent.db')
    if not Path(db_path).is_file():
        return None
    try:
        db = sqlite3.connect(f'file:{db_path}?mode=ro', uri=True)
        row = db.execute(
            "SELECT data FROM auth_credentials WHERE provider=?", (name,)).fetchone()
        return json.loads(row[0])['key'] if row else None
    except Exception:
        return None


def resolve(name: str):
    for src, fn in (('env', _from_env), ('keyfile', _from_keyfile), ('sqlite', _from_sqlite)):
        val = fn(name)
        if val:
            return src, val
    return None, None


def main() -> int:
    if len(sys.argv) < 3:
        print(__doc__.split('CLI：')[0], file=sys.stderr)
        return 2
    name, mode = sys.argv[1], sys.argv[2]
    src, val = resolve(name)
    if mode == 'probe':
        print(f'[secretsource] {name}: {"可用（来源 " + src + "）" if val else "不可用"}')
        return 0 if val else 1
    if not val:
        print(f'[secretsource] {name} 密钥不可用（env > ~/.radar-keys/{name} > sqlite 均未命中）',
              file=sys.stderr)
        return 1
    if mode == 'header':
        print(f'Authorization: Bearer {val}')
        return 0
    if mode == 'print':
        print(val)
        return 0
    print(f'[secretsource] 未知模式 {mode}', file=sys.stderr)
    return 2


if __name__ == '__main__':
    sys.exit(main())
