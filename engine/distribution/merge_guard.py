#!/usr/bin/env python3
"""merge_guard.py — 唯一自动合并门控（P4b；二轮外审加固）。

三重身份闸门（任一不过即拒并留人工）：
  1) head 钉死：PR headRefOid == 推送方捕获 SHA；合并同样绑定（--match-head-commit，
     gh 不支持该参数时拒绝自动合并——fail-closed，不静默降级）；--auto 排队视为
     已受理（head 已钉死，排队期间换头即拒），不误报失败（二轮外审 P1）；
  2) 作者钉死 any-of：GITHUB_TOKEN 创建的 PR 作者随平台代际可能是
     app/github-actions（新 App 格式）或 github-actions[bot]（经典 bot 格式）——
     二者皆为仓库令牌身份、攻击者不可伪造，白名单任一匹配即过（严格相等比较）；
  3) 文件钉死两模式（fnmatch 对 '/'' 无感知，目录型模式收紧为"前缀 + 单层"）：
     --expect-file 精确集（cadence 交付）/ --allow-file 允许集（渲染与快照 PR）。

CLI：
  python3 merge_guard.py --repo R --pr N --expect-sha <sha> \
      (--author LOGIN …可重复 any-of) \
      (--expect-file PATTERN … | --allow-file PATTERN …) [--dry]
  退出码：0 = 已合并/已排队/可并（--dry）；1 = 拒绝；2 = 调用错误
"""
import argparse
import fnmatch
import json
import shutil
import subprocess
import sys


def _gh(gh_bin, args, timeout=60):
    return subprocess.run([gh_bin, *args], capture_output=True, text=True, timeout=timeout)


def _file_match(path: str, pattern: str) -> bool:
    """目录型模式（尾缀 /*）收紧为单层：catalog/all/* 不跨更深子目录（fnmatch 本身无 / 感知）。"""
    if pattern.endswith('/*'):
        prefix = pattern[:-2]
        rest = path[len(prefix):] if path.startswith(prefix) else None
        return rest is not None and rest.startswith('/') and '/' not in rest[1:] and len(rest) > 1
    return fnmatch.fnmatch(path, pattern)


def _match_files(files, patterns):
    missing = [f for f in files if not any(_file_match(f, p) for p in patterns)]
    uncovered = [p for p in patterns if not any(_file_match(f, p) for f in files)]
    return missing, uncovered


def verify(repo, pr, expect_sha, authors, expect_files=None, allow_files=None, gh_bin='gh'):
    """闸门判定。authors=身份白名单（any-of）；expect_files=精确集 / allow_files=允许集。"""
    r = _gh(gh_bin, ['pr', 'view', str(pr), '--repo', repo, '--json',
                     'headRefOid,author,files'])
    if r.returncode != 0:
        return False, f'PR 查询失败: {(r.stderr or "").strip()[:120]}'
    try:
        info = json.loads(r.stdout)
    except json.JSONDecodeError:
        return False, f'PR 查询返回非 JSON: {r.stdout[:120]}'
    head = info.get('headRefOid') or ''
    author_login = (info.get('author') or {}).get('login') or ''
    files = sorted(f.get('path') or '' for f in (info.get('files') or []))

    if not head or head != expect_sha:
        return False, f'head SHA 不符（期望 {expect_sha[:8]}，实际 {head[:8] or "未知"}）'
    if author_login not in authors:
        return False, f'作者 {author_login or "未知"} 不在管线身份白名单 {sorted(authors)}'
    if expect_files is not None:
        missing, uncovered = _match_files(files, expect_files)
        if missing or uncovered:
            return False, (f'文件集合与产物不符（PR 多出 {missing[:3]}；产物缺对应 {uncovered[:3]}）')
    elif allow_files is not None:
        missing, _ = _match_files(files, allow_files)
        if missing:
            return False, f'PR 含允许清单外文件 {missing[:3]}'
    else:
        return False, '未指定文件闸门模式（--expect-file 或 --allow-file）'
    return True, '三重闸门通过（head SHA + 作者白名单 + 文件）'


def _supports_match_head(gh_bin) -> bool:
    h = _gh(gh_bin, ['pr', 'merge', '--help'])
    return '--match-head-commit' in (h.stdout or '')


def merge(repo, pr, expect_sha, gh_bin='gh'):
    """合并绑定已验证提交。--auto 受理即视为成功（排队期间换头由服务端拒）；
    直合并路径回退确认 state=MERGED。gh 不支持 --match-head-commit 时拒绝（fail-closed）。"""
    if not _supports_match_head(gh_bin):
        return False, ('gh 不支持 --match-head-commit（版本过旧）——拒绝自动合并，'
                       'fail-closed 不降级')
    base = ['pr', 'merge', str(pr), '--repo', repo, '--merge',
            '--match-head-commit', expect_sha]
    r = _gh(gh_bin, [*base, '--auto'], timeout=120)
    if r.returncode == 0:
        return True, '已受理自动合并（--auto 排队；head 已钉死，排队期间换头即拒）'
    r = _gh(gh_bin, base, timeout=120)
    if r.returncode != 0:
        return False, '合并命令失败（--auto 与直合并均败）'
    v = _gh(gh_bin, ['pr', 'view', str(pr), '--repo', repo, '--json', 'state'])
    merged = '"MERGED"' in (v.stdout or '')
    return merged, ('直合并确认' if merged else f'合并未确认（state={v.stdout.strip()[:40]}）')


def main() -> int:
    ap = argparse.ArgumentParser(description='三重闸门自动合并门控（唯一实现）')
    ap.add_argument('--repo', required=True)
    ap.add_argument('--pr', required=True)
    ap.add_argument('--expect-sha', required=True, help='推送方捕获的分支 commit（40 位；缺此应留人工，不降级）')
    ap.add_argument('--author', action='append', required=True,
                    help='管线身份白名单（可重复 any-of：app/github-actions 与 github-actions[bot] 皆可）')
    ap.add_argument('--expect-file', action='append', help='产物文件（精确集模式；glob 支持）')
    ap.add_argument('--allow-file', action='append', help='允许文件（允许集模式；清单无需全出现）')
    ap.add_argument('--dry', action='store_true', help='只判定不合并')
    ap.add_argument('--gh-bin', default=shutil.which('gh') or 'gh')
    a = ap.parse_args()
    if bool(a.expect_file) == bool(a.allow_file):
        print('[merge-guard] 必须且只能指定一种文件模式（--expect-file 或 --allow-file）', file=sys.stderr)
        return 2

    ok, reason = verify(a.repo, a.pr, a.expect_sha, set(a.author),
                        expect_files=a.expect_file, allow_files=a.allow_file, gh_bin=a.gh_bin)
    tag = f'[merge-guard] {a.repo}#{a.pr}'
    if not ok:
        print(f'{tag} 拒绝自动合并：{reason} → 留人工')
        return 1
    print(f'{tag} {reason}')
    if a.dry:
        return 0
    merged, m_reason = merge(a.repo, a.pr, a.expect_sha, a.gh_bin)
    print(f'{tag} {m_reason}')
    return 0 if merged else 1


if __name__ == '__main__':
    sys.exit(main())
