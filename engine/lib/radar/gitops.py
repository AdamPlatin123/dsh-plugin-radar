#!/usr/bin/env python3
"""gitops — git 子进程封装（P3；push 只允许租约式）。

背景：cadence.py 曾同时传 --force-with-lease 与 --force，后者使租约保护
失效（P2b 已移除字面量）；本模块从接口层面杜绝复发——push 一律带
--force-with-lease，不存在任何裸 --force 通路。
"""
import subprocess


def sh(args, cwd=None, timeout=120, env=None):
    """统一子进程调用（capture 输出；调用方自管返回码语义）。"""
    assert isinstance(args, list)
    return subprocess.run(args, capture_output=True, text=True, cwd=cwd,
                          timeout=timeout, env=env)


def push(remote, branch, cwd=None, timeout=120, env=None):
    """租约式推送：远端被他人推进则拒绝覆盖（exit 非 0），绝不裸 --force。"""
    return sh(['git', 'push', '-q', '--force-with-lease', remote, branch],
              cwd=cwd, timeout=timeout, env=env)


def worktree_remove(path, cwd=None):
    """清理 worktree（允许 --force：对本地临时工作树，语义为丢弃而非覆盖远端）。"""
    return sh(['git', 'worktree', 'remove', '--force', str(path)], cwd=cwd)
