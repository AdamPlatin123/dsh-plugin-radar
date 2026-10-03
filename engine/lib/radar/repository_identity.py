"""按已核实的 GitHub 仓库编号和别名归一身份，不按项目名、星数或 fork 关系合并。"""
import json
import re
from collections import defaultdict

REPO = re.compile(r'^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$')


def _read(path):
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding='utf8'))


class RepositoryIdentities:
    def __init__(self, repo_map=None, enrich=None, verified=None):
        observations = []
        for item in (repo_map or {}).values():
            if not item.get('full_name'):
                continue
            observations.append((1, '', item, item.get('aliases') or []))
        for repo, item in (enrich or {}).items():
            if item.get('canonical_id') and item.get('full_name'):
                observations.append((2, item.get('identity_checked_at') or '', item, [repo]))
        for item in verified or []:
            observations.append((3, item.get('checked_at') or '', item, item.get('aliases') or []))

        groups = defaultdict(list)
        for priority, checked, item, aliases in observations:
            full = item.get('full_name') or ''
            if not REPO.fullmatch(full):
                raise ValueError(f'Invalid repository identity: {full!r}')
            identity = item.get('canonical_id') or full.lower()
            groups[identity].append((priority, checked, full, aliases))
        direct = {}
        for records in groups.values():
            current = max(records, key=lambda r: (r[1], r[0], r[2].lower()))[2]
            for priority, checked, full, aliases in records:
                for alias in [full, *aliases]:
                    if not REPO.fullmatch(alias):
                        raise ValueError(f'Invalid repository alias: {alias!r}')
                    key = alias.lower()
                    candidate = (checked, priority, current)
                    if key not in direct or candidate[:2] > direct[key][:2]:
                        direct[key] = candidate
                    elif candidate[:2] == direct[key][:2] and current.lower() != direct[key][2].lower():
                        raise ValueError(f'Conflicting repository identity: {alias}')
        self.aliases = {}
        for alias in direct:
            target, seen = alias, set()
            while target.lower() in direct:
                key = target.lower()
                current = direct[key][2]
                if current.lower() == key:
                    target = current
                    break
                if key in seen:
                    raise ValueError(f'Repository alias cycle: {alias}')
                seen.add(key)
                target = current
            if alias != target.lower():
                self.aliases[alias] = target

    @classmethod
    def load(cls, root):
        return cls(
            _read(root / 'data/repo-map.json').get('entries', {}),
            _read(root / 'data/plugins-enrich.json').get('entries', {}),
            _read(root / 'data/repository-identities.json').get('entries', []),
        )

    def resolve(self, repo):
        return self.aliases.get(repo.lower(), repo)


def dedupe_public_rows(rows, identities):
    """写入前归一地址、归并标签和星数；不一致且含运行结论的记录保守降为待定。"""
    groups, verdicts = {}, defaultdict(set)
    for row in rows:
        repo = identities.resolve(row['repo'])
        key = repo.lower()
        verdicts[key].add(row['verdict'])
        if key not in groups:
            groups[key] = dict(row, repo=repo)
            continue
        prev = groups[key]
        if row.get('stars') is not None and (prev.get('stars') is None or row['stars'] > prev['stars']):
            prev['stars'] = row['stars']
        if not prev.get('desc') or prev['desc'] == '—':
            prev['desc'] = row.get('desc') or '—'
        for marker in ('〔PR〕', '〔📦〕'):
            if marker in (row.get('desc') or '') and marker not in prev['desc']:
                prev['desc'] += marker
    for key, row in groups.items():
        if len(verdicts[key]) > 1 and verdicts[key] & {'ok', 'incompatible'}:
            row['verdict'] = 'pending'
    return list(groups.values())
