#!/usr/bin/env python3
"""Acceptance tests for harness-kit/scripts/harness-selftest (mutation-testing tool).

Uses a real `harness-init --profile standard` host (temporary git repo) and runs the
real CLI. No network, no Xcode; standard library only.
Run: python3 -m unittest discover -s harness-kit/tests -q
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

KIT = Path(__file__).resolve().parents[1]
SELFTEST = KIT / "scripts" / "harness-selftest"
INIT = KIT / "scripts" / "harness-init"

# Synthetic markers are built from parts so the test file carries no local absolute paths.
USER_MARKER = "/Us" + "ers/selftest"
VOLUME_MARKER = "/Vol" + "umes/selftest"


def run(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True, timeout=300)


def git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return run(["git", *args], cwd=repo)


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def init_git(repo: Path) -> None:
    repo.mkdir(parents=True, exist_ok=True)
    assert git(repo, "init", "-q").returncode == 0
    for key, value in (("user.name", "kit-test"), ("user.email", "kit-test@example.invalid")):
        assert git(repo, "config", key, value).returncode == 0


def commit_all(repo: Path, message: str) -> None:
    assert git(repo, "add", "-A").returncode == 0
    assert git(repo, "commit", "-q", "-m", message).returncode == 0


def build_standard_host(root: Path) -> Path:
    """Generate a clean standard-profile host with committed scaffold (no network)."""
    host = root / "host"
    init_git(host)
    write(host / "README.md", "# Host project\n")
    write(host / "app.py", "def main():\n    return 0\n")
    commit_all(host, "init")
    proc = run(
        [
            sys.executable, str(INIT),
            "--profile", "standard",
            "--target", str(host),
            "--language", "python",
            "--test-command", "python3 -m unittest discover -q",
            "--no-check",
        ],
        cwd=KIT,
    )
    if proc.returncode != 0:
        raise AssertionError(f"harness-init failed:\n{proc.stdout}\n{proc.stderr}")
    commit_all(host, "scaffold")
    return host


def active_plan_body() -> str:
    return (
        "---\n"
        "id: 2026-01-01-demo\n"
        "status: active\n"
        "level: L2\n"
        "owner: test\n"
        "updated: 2026-01-01\n"
        "scope:\n"
        "  allow:\n"
        "    - harness/\n"
        "acceptance:\n"
        "  - python3 tools/check_docs.py\n"
        "verify:\n"
        "  - make check\n"
        "---\n\n"
        "# Demo plan\n\n"
        "## 目标与非目标\n\n- 目标：条件 mutation 验证\n\n"
        "## 验收\n\n- make check 通过\n\n"
        "## 验证证据\n\n"
        "| 命令 | 结果 | 环境 | 证据ID |\n"
        "| --- | --- | --- | --- |\n"
        "| `make check` | 基线盘点 | 本机 | —（基线盘点） |\n\n"
        "## 未提交改动\n\n- 无未提交改动\n\n"
        "## 下一步\n\n1. 继续\n"
    )


def augment_host_with_conditionals(host: Path) -> None:
    """Add active plan + evidence + hygiene config/gate so M6/M7/M8 become applicable."""
    config_path = host / "harness" / "config.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    claim_name = config["claims"][0]["name"]
    write(host / "harness" / "plans" / "2026-01-01-demo.md", active_plan_body())
    evidence = {
        "schemaVersion": 1,
        "id": f"20260101T000000Z-{claim_name}",
        "claim": claim_name,
        "createdAt": "2026-01-01T00:00:00Z",
        "git": {"commit": "0000000", "dirty": False},
        "command": "make check",
        "environment": {"xcode": None, "simulator": None, "device": None},
        "result": {
            "status": "SUCCEEDED", "passed": 1, "failed": 0, "skipped": 0,
            "durationSec": 0.1, "xcresultPath": "build/test.xcresult",
        },
        "verdict": "PASS",
        "verifier": "tools/evidence.py@test",
    }
    write(host / "harness" / "evidence" / f"{evidence['id']}.json", json.dumps(evidence, indent=2))
    config["hygiene"] = {"enabled": True}
    config_path.write_text(json.dumps(config, indent=2), encoding="utf-8")
    write(
        host / "tools" / "check_hygiene.py",
        '#!/usr/bin/env python3\n'
        "import subprocess, sys\n"
        f'marker = "{VOLUME_MARKER}"\n'
        'files = subprocess.run(["git", "ls-files"], capture_output=True, text=True).stdout.split()\n'
        "bad = []\n"
        "for name in files:\n"
        "    try:\n"
        '        if marker in open(name, encoding="utf-8", errors="ignore").read():\n'
        "            bad.append(name)\n"
        "    except OSError:\n"
        "        pass\n"
        'if bad:\n'
        '    print("[FAIL] local marker in:", bad[:3])\n'
        "    sys.exit(1)\n"
        'print("[OK] hygiene")\n'
        "sys.exit(0)\n",
    )
    commit_all(host, "conditionals")


class HarnessSelftestTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._tmp = tempfile.TemporaryDirectory()
        cls.tmp = Path(cls._tmp.name)
        cls.host = build_standard_host(cls.tmp)

    @classmethod
    def tearDownClass(cls) -> None:
        cls._tmp.cleanup()

    def invoke(self, target: Path, *args: str) -> subprocess.CompletedProcess[str]:
        return run([sys.executable, str(SELFTEST), "--target", str(target), *args], cwd=KIT)

    def combined(self, proc: subprocess.CompletedProcess[str]) -> str:
        return proc.stdout + proc.stderr

    # ── normal host ─────────────────────────────────────────────────
    def test_clean_host_passes_with_mutation_matrix(self) -> None:
        proc = self.invoke(self.host)
        self.assertEqual(proc.returncode, 0, self.combined(proc))
        output = proc.stdout
        self.assertIn("M1", output)
        self.assertIn("M5", output)
        self.assertIn("tools/check_docs.py", output)
        self.assertIn("recovery:", output)
        self.assertIn("RESULT PASS", output)
        # The target repository itself must stay untouched (the tool works on a clone).
        status = git(self.host, "status", "--porcelain", "--untracked-files=all").stdout
        self.assertEqual("", status.strip(), "harness-selftest must not modify the target")

    def test_json_report_contract(self) -> None:
        proc = self.invoke(self.host, "--json")
        self.assertEqual(proc.returncode, 0, self.combined(proc))
        data = json.loads(proc.stdout)
        for key in ("tool", "target", "baseline", "mutations", "recovery", "summary", "ok", "exitCode"):
            self.assertIn(key, data)
        self.assertTrue(data["ok"])
        self.assertEqual(0, data["exitCode"])
        ids = [item["id"] for item in data["mutations"]]
        self.assertEqual(["M1", "M2", "M3", "M4", "M5", "M6", "M7", "M8", "M9"], ids)

    # ── dirty target ────────────────────────────────────────────────
    def test_dirty_target_exits_two(self) -> None:
        readme = self.host / "README.md"
        original = readme.read_text(encoding="utf-8")
        try:
            readme.write_text(original + "\nuncommitted change\n", encoding="utf-8")
            proc = self.invoke(self.host)
            self.assertEqual(proc.returncode, 2, self.combined(proc))
            self.assertIn("干净", self.combined(proc))
        finally:
            git(self.host, "checkout", "--", ".")
            self.assertEqual("", git(self.host, "status", "--porcelain").stdout.strip())

    # ── red baseline ────────────────────────────────────────────────
    def test_red_baseline_exits_two(self) -> None:
        red_host = self.tmp / "red-host"
        shutil.copytree(self.host, red_host)
        write(red_host / "docs" / "unregistered.md", "# unregistered\n")
        commit_all(red_host, "break baseline: unregistered doc")
        proc = self.invoke(red_host)
        self.assertEqual(proc.returncode, 2, self.combined(proc))
        self.assertIn("baseline", self.combined(proc))

    # ── conditional mutations M6/M7/M8 ─────────────────────────────
    def test_conditional_mutations_are_exercised(self) -> None:
        conditional_host = self.tmp / "conditional-host"
        shutil.copytree(self.host, conditional_host)
        augment_host_with_conditionals(conditional_host)
        proc = self.invoke(conditional_host)
        self.assertEqual(proc.returncode, 0, self.combined(proc))
        output = proc.stdout
        for mutation_id in ("M6", "M7", "M8", "M9"):
            line = next((line for line in output.splitlines() if line.startswith(mutation_id)), "")
            self.assertIn("PASS", line, f"{mutation_id} should be exercised, output:\n{output}")
        self.assertIn("RESULT PASS", output)


if __name__ == "__main__":
    unittest.main()
