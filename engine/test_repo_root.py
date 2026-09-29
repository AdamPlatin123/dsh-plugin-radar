import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def resolved_root(source: Path) -> Path:
    line = next(
        item for item in source.read_text(encoding="utf-8").splitlines()
        if item.startswith("ROOT = ")
    )
    namespace = {"__file__": str(source)}
    exec("from pathlib import Path\n" + line, namespace)
    return namespace["ROOT"]


class EngineRootTest(unittest.TestCase):
    def test_engine_scripts_use_repository_root(self):
        for rel in (
            "engine/discovery/discover.py",
            "engine/aggregation/aggregate.py",
            "engine/aggregation/normalize.py",
        ):
            self.assertEqual(resolved_root(REPO / rel), REPO)
        self.assertTrue((REPO / "PLUGINS.md").is_file())
        self.assertTrue((REPO / "catalog" / "plugins").is_dir())

    def test_discover_callers_use_the_moved_script(self):
        entry = "engine/discovery/discover.py"
        for rel in (
            "engine/ops/radar-watchdog.sh",
            "scripts/gen-pipeline-diagram.py",
            "engine/README.md",
        ):
            text = (REPO / rel).read_text(encoding="utf-8")
            self.assertIn(entry, text)
            self.assertNotIn("scripts/discover.py", text)


if __name__ == "__main__":
    unittest.main()
