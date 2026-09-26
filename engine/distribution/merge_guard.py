#!/usr/bin/env python3
"""merge_guard.py — 唯一自动合并门控（P4b；外审 P0-4/P1-2 加固）。

三重身份闸门（任一不过即拒并留人工）：
  1) head 钉死：PR 的 headRefOid 必须等于推送方捕获的 commit SHA——防同名伪装 PR
     劫持；合并执行同样绑定该 SHA（gh --match-head-commit），验证与合并之间
     分支换头即拒绝（TOCTOU 关闭）；
  2) 作者钉死：PR 作者必须是本管线认证账号（注意 GITHUB_TOKEN 创建的 PR
     作者为 app/github-actions，非触发者 github.actor——外审 P1）；
  3) 文件钉死，两种模式（外审 P1-2：允许产物 ≠ 每轮必须全部出现）：
     --expect-file 精确集：PR 文件集合精确等于产物清单（cadence 交付：
     产物清单即本轮实际全集）；
     --allow-file 允许集：PR 每个文件都 ∈ 允许清单即可，清单无需全出现
     （渲染/快照 PR：磁贴或目录本轮无变化属正常）。

CLI：
  python3 merge_guard.py --repo R --pr N --expect-sha <sha> --author <login> \
      (--expect-file PATTERN … | --allow-file PATTERN …) [--dry]
  退出码：0 = 已合并/可并（--dry）；1 = 拒绝（原因见输出）；2 = 调用错误
"""
import argparse
import fnmatch
import json
import shutil
import subprocess
import sys


def _gh(gh_bin, args, timeout=60):
    return subprocess.run([gh_bin, *args], capture_output=True, text=True, timeout=timeout)


def _match_files(files, patterns):
    missing = [f for f in files if not any(fnmatch.fnmatch(f, p) for p in patterns)]
    uncovered = [p for p in patterns if not any(fnmatch.fnmatch(f, p) for f in files)]
    return missing, uncovered


def verify(repo, pr, expect_sha, author, expect_files=None, allow_files=None, gh_bin='gh'):
    """闸门判定。返回 (ok, reason)。expect_files=精确集 / allow_files=允许集（二选一）。"""
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
        return False, (f'head SHA 不符（期望 {expect_sha[:8]}，'
                       f'实际 {head[:8] or "未知"}）')
    if author_login != author:
        return False, f'作者 {author_login or "未知"} 非本管线账号 {author}'
    if expect_files is not None:
        missing, uncovered = _match_files(files, expect_files)
        if missing or uncovered:
            return False, (f'文件集合与产物不符（PR 多出 {missing[:3]}；'
                           f'产物缺对应 {uncovered[:3]}）')
    elif allow_files is not None:
        missing, _ = _match_files(files, allow_files)
        if missing:
            return False, f'PR 含允许清单外文件 {missing[:3]}'
    else:
        return False, '未指定文件闸门模式（--expect-file 或 --allow-file）'
    return True, '三重闸门通过（head SHA + 作者 + 文件）'


def merge(repo, pr, expect_sha, gh_bin='gh'):
    """合并绑定已验证提交：--match-head-commit 确保排队期间分支换头即拒绝；
    --auto 优先 → 直合并回退 → state 确认。"""
    base = ['pr', 'merge', str(pr), '--repo', repo, '--merge',
            '--match-head-commit', expect_sha]
    r = _gh(gh_bin, [*base, '--auto'], timeout=120)
    if r.returncode != 0:
        r = _gh(gh_bin, base, timeout=120)
        if r.returncode != 0:
            return False, '合并命令失败（--auto 与直合并均败）'
    v = _gh(gh_bin, ['pr', 'view', str(pr), '--repo', repo, '--json', 'state'])
    merged = '"MERGED"' in (v.stdout or '')
    return merged, ('自动合并确认（head 已钉死）' if merged
                    else f'合并未确认（state={v.stdout.strip()[:40]}）')


def main() -> int:
    ap = argparse.ArgumentParser(description='三重闸门自动合并门控（唯一实现）')
    ap.add_argument('--repo', required=True)
    ap.add_argument('--pr', required=True)
    ap.add_argument('--expect-sha', required=True,
                    help='推送方捕获的分支 commit（全 40 位；缺此项应留人工，不降级）')
    ap.add_argument('--author', required=True, help='本管线认证账号 login（GITHUB_TOKEN PR 为 app/github-actions）')
    ap.add_argument('--expect-file', action='append',
                    help='产物文件（精确集模式；可重复；glob 支持）')
    ap.add_argument('--allow-file', action='append',
                    help='允许文件（允许集模式：PR 文件 ∈ 清单即可，清单无需全出现）')
    ap.add_argument('--dry', action='store_true', help='只判定不合并')
    ap.add_argument('--gh-bin', default=shutil.which('gh') or 'gh')
    a = ap.parse_args()
    if bool(a.expect_file) == bool(a.allow_file):
        print('[merge-guard] 必须且只能指定一种文件模式（--expect-file 或 --allow-file）', file=sys.stderr)
        return 2

    ok, reason = verify(a.repo, a.pr, a.expect_sha, a.author,
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
