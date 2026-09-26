#!/usr/bin/env python3
"""validate_contracts.py — 稳定数据接口契约校验（P0 安全网）。

对 data/latest.json 与 data/plugins-all.json 执行 schema/radar-v1.schema.json
的正式契约校验（jsonschema draft-07），另加跨文件语义断言。

设计动机：runner_versions 曾以「合法 JSON 的 API 404 错误对象」身份混入稳定接口
随渲染链发布（try/except 只防解析失败、防不住错误内容）——契约校验进 CI 后此类
事故在合入前即被拦截。

用法：python3 scripts/validate_contracts.py [repo-root]
依赖：pip install jsonschema（仅 CI/开发环境需要；引擎运行时零依赖不变）
"""
import json
import sys
from pathlib import Path

SCHEMA_FILE = 'schema/radar-v1.schema.json'
TARGETS = [
    ('data/latest.json', '#/definitions/latest'),
    ('data/plugins-all.json', '#/definitions/plugins_all'),
]


def validate(root: Path) -> int:
    try:
        import jsonschema
    except ImportError:
        print('[contracts] 缺少 jsonschema：pip install jsonschema', file=sys.stderr)
        return 3

    schema = json.loads((root / SCHEMA_FILE).read_text(encoding='utf8'))
    resolver = jsonschema.RefResolver.from_schema(schema)
    failed = False
    docs = {}
    for rel, ref in TARGETS:
        path = root / rel
        if not path.exists():
            print(f'[contracts] 缺文件：{rel}', file=sys.stderr)
            failed = True
            continue
        doc = json.loads(path.read_text(encoding='utf8'))
        docs[rel] = doc
        validator = jsonschema.Draft7Validator(
            resolver.resolve(ref)[1], resolver=resolver)
        errors = sorted(validator.iter_errors(doc), key=lambda e: list(e.absolute_path))
        if errors:
            failed = True
            for e in errors[:10]:
                loc = '/'.join(str(p) for p in e.absolute_path) or '<root>'
                print(f'[contracts] {rel}#{loc}: {e.message}', file=sys.stderr)
        else:
            print(f'[contracts] {rel} 契约通过（{ref}）')

    # 跨文件语义断言：total_listed 必须等于清单实际条数
    latest = docs.get('data/latest.json')
    plugins = docs.get('data/plugins-all.json')
    if latest and plugins:
        n_claim, n_real = latest['total_listed'], len(plugins['plugins'])
        if n_claim != n_real:
            print(f'[contracts] latest.total_listed={n_claim} 与 plugins 实际 {n_real} 不符',
                  file=sys.stderr)
            failed = True
        else:
            print(f'[contracts] 跨文件一致：total_listed={n_claim}')
    return 1 if failed else 0


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else '.')
    return validate(root)


if __name__ == '__main__':
    raise SystemExit(main())
