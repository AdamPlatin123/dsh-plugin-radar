"""atomicio — 唯一原子写实现（P1 引入；替代散布各处的 tmp+replace 手写）。

历史现状：tmp.replace 模式在 discover.py / aggregate.py / normalize.py / cadence.py
各有一份手写副本。本模块收敛为唯一实现；存量调用在 P3 分批迁移，新代码一律用它。
"""
import os
from pathlib import Path


def atomic_write_text(path: Path, text: str, *, encoding: str = 'utf8') -> None:
    """同目录临时文件写入 + os.replace 原子落盘（读者永远看不到半截文件）。"""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + '.tmp')
    with open(tmp, 'w', encoding=encoding) as f:
        f.write(text)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def atomic_write_json(path: Path, doc, *, indent: int = 2, ensure_ascii: bool = False) -> None:
    """JSON 文档原子写（ensure_ascii=False 与仓内其余产物口径一致）。"""
    import json
    atomic_write_text(path, json.dumps(doc, ensure_ascii=ensure_ascii, indent=indent) + '\n')
