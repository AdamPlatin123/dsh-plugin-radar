#!/usr/bin/env python3
"""ghql — GitHub GraphQL 批量客户端（P3 自 scripts/refresh-stars.py 收敛为唯一实现）。

改进（相对被收敛的原内联版）：
- urllib 直连替代 curl 子进程——token 走请求头对象，永不进 argv（ps 不可见）
- 限速感知：响应头 x-ratelimit-remaining < 500 时 sleep 至 reset 窗再继续
- 字段参数化（P6 补采管线将同批扩 pushedAt/avatarUrl/topics 等字段，配额零增量）
- 保留原语义：整批失败重试一次（代理偶发）；GraphQL 改名捕获 + REST 301 回退

依赖：纯标准库。token：GH_TOKEN 环境变量 > `gh auth token`。
"""
import json
import os
import subprocess
import sys
import time
import urllib.request

API = 'https://api.github.com/graphql'
RATE_FLOOR = 500          # 余量低于此值即等待重置窗
SLEEP_LOGGED = {'last': 0}   # 限速等待日志节流（每轮任务最多提示一次）


def resolve_token():
    tok = os.environ.get('GH_TOKEN')
    if tok:
        return tok
    try:
        return subprocess.run(['gh', 'auth', 'token'], capture_output=True,
                              text=True, timeout=15).stdout.strip()
    except Exception:
        return ''


def _post(query: str, token: str):
    """单次 GraphQL POST；返回 (data, headers)。限速感知睡眠内置。"""
    req = urllib.request.Request(
        API, data=json.dumps({'query': query}).encode(),
        headers={'Authorization': f'Bearer {token}',
                 'Content-Type': 'application/json',
                 'User-Agent': 'dsh-plugin-radar/ghql'})
    with urllib.request.urlopen(req, timeout=30) as resp:
        remaining = resp.headers.get('x-ratelimit-remaining')
        if remaining is not None and int(remaining) < RATE_FLOOR:
            reset = int(resp.headers.get('x-ratelimit-reset') or (time.time() + 3600))
            wait = max(0, reset - time.time()) + 2
            if time.time() - SLEEP_LOGGED['last'] > 600:
                print(f'[ghql] 限速余量 {remaining}，睡眠 {wait/60:.0f} 分钟至重置窗', file=sys.stderr)
                SLEEP_LOGGED['last'] = time.time()
            time.sleep(wait)
        return json.loads(resp.read().decode())


def gql_batch(repos, token=None, fields='stargazerCount nameWithOwner', on_rename=None):
    """一批查询：[(owner, name)] → {full_name_lower: {field: value…}}。

    on_rename(old_lower, new_full_name) 在 GraphQL 解析名与请求名不符时回调（改名捕获）。
    整批失败重试一次；两次皆败返回 {}（调用方守门：解析率过低时中止）。
    """
    token = token or resolve_token()
    if not token or not repos:
        return {}
    parts = [f'r{i}: repository(owner:"{o}",name:"{n}"){{ {fields} }}'
             for i, (o, n) in enumerate(repos)]
    query = '{ ' + ' '.join(parts) + ' }'
    data = None
    for _attempt in (1, 2):   # 代理下批量查询偶发整批失败：重试一次
        try:
            payload = _post(query, token)
            data = payload.get('data') or {}
            if data:
                break
            if payload.get('errors'):
                print('[ghql] errors:', str(payload['errors'])[:300], file=sys.stderr)
        except Exception as exc:
            print(f'[ghql] 请求失败（第 {_attempt} 次）: {exc}', file=sys.stderr)
            data = None
    if data is None:
        return {}
    out = {}
    for i, (o, n) in enumerate(repos):
        node = data.get(f'r{i}')
        if node is not None:
            key = f'{o}/{n}'.lower()
            out[key] = node
            full = (node.get('nameWithOwner') or '').strip()
            if full and full.lower() != key and on_rename:
                on_rename(key, full)   # GraphQL 解析名与请求名不符 = 已改名
    return out


def rest_repo(owner: str, name: str, token=None):
    """REST /repos/<o>/<n>（跟随 301 改名）；返回 dict 或 None。GraphQL 旧名 null 的兜底。"""
    token = token or resolve_token()
    req = urllib.request.Request(
        f'https://api.github.com/repos/{owner}/{name}',
        headers={'Authorization': f'Bearer {token}',
                 'User-Agent': 'dsh-plugin-radar/ghql'})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode())
    except Exception:
        return None
