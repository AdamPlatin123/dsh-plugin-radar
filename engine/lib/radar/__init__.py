"""radar — 雷达引擎公共库（P3 lib 层的唯一实现来源）。

引擎各域脚本统一经 engine/lib 注入 sys.path 后 import：
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'lib'))
    from radar import atomicio

设计约束：纯标准库（引擎运行环境零第三方依赖）；任何惯用法在本包内只允许一份实现。
"""
