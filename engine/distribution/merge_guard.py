#!/usr/bin/env python3
"""merge_guard.py — 唯一自动合并门控（P4b；此前四处实现强度不一）。

三重身份闸门（任一不过即拒并留人工）：
  1) head 钉死：PR 的 headRefOid 必须等于推送方捕获的 commit SHA——防同名伪装 PR
     劫持（白名单校验只看文件集合，攻击者可开同名分支塞白名单文件）；
  2) 作者钉死：PR 作者必须是本管线认证账号；
  3) 文件钉死：PR 文件集合必须精确等于本管线产物清单（glob 支持 catalog/all/* 类目录），
     而非"前缀白名单内即放行"。

合并执行：--auto 优先（依赖仓库 allow_auto_merge），失败回退直合并，最终确认
state=MERGED 才算成功。

历史强度谱（收敛前）：cadence.py 三重闸门（本标准）＞ readme-render.yml 精确文件
枚举 ≈ auto-merge-render.sh 精确枚举 ＞ bot-deliver.sh 前缀白名单（最弱，已升级）。

CLI：
  python3 engine/distribution/merge_guard.py --repo R --pr N \
      --expect-sha <full-sha> --author <login> \
      --expect-file data/snapshots/20260926T111047Z.json --expect-file 'reports/*' \
      [--dry]          # 只判定不合并
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


def verify(repo, pr, expect_sha, author, expect_files, gh_bin='gh'):
    """闸门判定。返回 (ok, reason)；reason 为人读拒绝原因或通过描述。"""
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
    missing = [f for f in files
               if not any(fnmatch.fnmatch(f, pat) for pat in expect_files)]
    extra_expect = [p for p in expect_files
                    if not any(fnmatch.fnmatch(f, p) for f in files)]
    if missing or extra_expect:
        return False, (f'文件集合与产物不符（PR 多出 {missing[:3]}；'
                       f'产物缺对应 {extra_expect[:3]}）')
    return True, '三重闸门通过（head SHA + 作者 + 文件集合）'


def merge(repo, pr, gh_bin='gh'):
    """--auto 优先 → 直合并回退 → state 确认。返回 (merged, reason)。"""
    r = _gh(gh_bin, ['pr', 'merge', str(pr), '--repo', repo, '--merge', '--auto'],
            timeout=120)
    if r.returncode != 0:
        r = _gh(gh_bin, ['pr', 'merge', str(pr), '--repo', repo, '--merge'], timeout=120)
        if r.returncode != 0:
            return False, '合并命令失败（--auto 与直合并均败）'
    v = _gh(gh_bin, ['pr', 'view', str(pr), '--repo', repo, '--json', 'state'])
    merged = '"MERGED"' in (v.stdout or '')
    return merged, ('自动合并确认' if merged else f'合并未确认（state={v.stdout.strip()[:40]}）')


def main() -> int:
    ap = argparse.ArgumentParser(description='三重闸门自动合并门控（唯一实现）')
    ap.add_argument('--repo', required=True)
    ap.add_argument('--pr', required=True)
    ap.add_argument('--expect-sha', required=True,
                    help='推送方捕获的分支 commit（全 40 位；缺此项应留人工，不降级）')
    ap.add_argument('--author', required=True, help='本管线认证账号 login')
    ap.add_argument('--expect-file', action='append', required=True,
                    help='产物文件（可重复；支持 glob 如 reports/*）')
    ap.add_argument('--dry', action='store_true', help='只判定不合并')
    ap.add_argument('--gh-bin', default=shutil.which('gh') or 'gh')
    a = ap.parse_args()

    ok, reason = verify(a.repo, a.pr, a.expect_sha, a.author, a.expect_file, a.gh_bin)
    tag = f'[merge-guard] {a.repo}#{a.pr}'
    if not ok:
        print(f'{tag} 拒绝自动合并：{reason} → 留人工')
        return 1
    print(f'{tag} {reason}')
    if a.dry:
        return 0
    merged, m_reason = merge(a.repo, a.pr, a.gh_bin)
    print(f'{tag} {m_reason}')
    return 0 if merged else 1


if __name__ == '__main__':
    sys.exit(main())
