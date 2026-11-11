#!/usr/bin/env python3
"""Kit prompt library tests: front matter contract, generated doc, CLI composition.

Contract: harness-kit/SPEC.md §9. Standard library only; no network.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

KIT = Path(__file__).resolve().parents[1]
SCRIPT = KIT / "scripts" / "harness-prompt"
PROMPTS = KIT / "prompts"
DOC = KIT / "docs" / "agent-prompts.md"
PLACEHOLDER_RE = re.compile(r"\{\{([A-Z0-9_]+)\}\}")
STAGE_LABELS = {"unadopted", "adopted", "any"}
REQUIRED = ("id", "title", "short", "number", "group", "stage", "kind", "when")


def run_prompt(args, *, cwd=KIT, env=None):
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True, text=True, cwd=cwd, env=env,
    )


ANGLE_TOKEN_RE = re.compile(r"<([^<>\s][^<>\n]{0,40})>")


def make_adopted_target(root: Path) -> Path:
    """v0.4.0：manifest 是真源；按 minimal profile 的期望文件集建 fixture。"""
    root.mkdir(parents=True, exist_ok=True)
    profile = json.loads((KIT / "profiles" / "minimal.json").read_text(encoding="utf-8"))
    files = []
    for item in profile["files"]:
        destination = item["dst"]
        path = root / destination
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("# fixture\n", encoding="utf-8")
        files.append({"path": destination, "sha256": "0" * 64, "src": item["src"]})
    (root / "Makefile").write_text("# fixture\n", encoding="utf-8")
    manifest = {
        "schemaVersion": 1,
        "kitVersion": "0.4.0",
        "profile": "minimal",
        "generatedAt": "2026-01-01T00:00:00Z",
        "files": files,
        "appends": [],
        "skipped": [],
    }
    (root / ".harness-manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return root


def parse_front_matter(path: Path) -> tuple[dict[str, str], str]:
    text = path.read_text(encoding="utf-8")
    assert text.startswith("---\n"), f"{path}: missing front matter"
    end = text.find("\n---\n", 4)
    assert end >= 0, f"{path}: unterminated front matter"
    meta: dict[str, str] = {}
    for line in text[4:end].splitlines():
        if line.strip():
            key, _, value = line.partition(":")
            meta[key.strip()] = value.strip()
    return meta, text[end + 5:]


class PromptSourceTests(unittest.TestCase):
    """Source-of-truth contract for prompts/*.md (independent of the CLI)."""

    def prompt_files(self) -> list[Path]:
        return sorted(path for path in PROMPTS.glob("*.md") if not path.name.startswith("_"))

    def test_front_matter_and_placeholders(self) -> None:
        self.assertEqual(21, len(self.prompt_files()), "expected 19 task + 2 addon prompt files")
        ids: set[str] = set()
        numbers: set[int] = set()
        for path in self.prompt_files():
            meta, body = parse_front_matter(path)
            for key in REQUIRED:
                self.assertIn(key, meta, f"{path.name}: missing {key}")
            self.assertEqual(path.stem, meta["id"], f"{path.name}: id must equal file stem")
            self.assertIn(meta["stage"], STAGE_LABELS, f"{path.name}: bad stage")
            self.assertIn(meta["kind"], {"task", "addon"}, f"{path.name}: bad kind")
            if meta["kind"] == "task":
                self.assertIn(meta["stage"], {"unadopted", "adopted"}, f"{path.name}: task stage")
                self.assertTrue(meta.get("returns"), f"{path.name}: task needs returns")
                self.assertTrue(meta.get("fail_signal"), f"{path.name}: task needs fail_signal")
            else:
                self.assertEqual("any", meta["stage"], f"{path.name}: addon stage must be any")
            self.assertNotIn(meta["id"], ids, "duplicate id")
            ids.add(meta["id"])
            self.assertNotIn(int(meta["number"]), numbers, "duplicate number")
            numbers.add(int(meta["number"]))
            declared = [item.strip() for item in meta.get("placeholders", "").split(",") if item.strip()]
            found = sorted(set(PLACEHOLDER_RE.findall(body)) - {"KIT", "TARGET"})
            self.assertEqual(sorted(declared), found, f"{path.name}: placeholders metadata != body")

    def test_preambles_are_stage_scoped(self) -> None:
        adopted = (PROMPTS / "_preamble-adopted.md").read_text(encoding="utf-8")
        adoption = (PROMPTS / "_preamble-adoption.md").read_text(encoding="utf-8")
        self.assertIn("已接入项目", adopted)
        self.assertIn("{{TARGET}}", adopted)
        self.assertNotIn("{{KIT}}", adopted)
        self.assertIn("未接入项目", adoption)
        self.assertIn("{{KIT}}", adoption)
        self.assertIn("{{TARGET}}", adoption)
        for text in (adopted, adoption):
            self.assertEqual([], sorted(set(PLACEHOLDER_RE.findall(text)) - {"KIT", "TARGET"}))


class PromptDocTests(unittest.TestCase):
    """The public docs/agent-prompts.md must be a faithful render of prompts/."""

    def test_doc_is_up_to_date(self) -> None:
        process = run_prompt(["render", "--check"])
        self.assertEqual(0, process.returncode, process.stderr)
        self.assertIn("up to date", process.stdout)

    def test_every_prompt_has_a_section_and_table_row(self) -> None:
        doc = DOC.read_text(encoding="utf-8")
        inventory = json.loads(run_prompt(["list", "--json"]).stdout)
        for prompt in inventory["prompts"]:
            self.assertIn(f"## {prompt['number']}. {prompt['title']}", doc)
            if prompt["kind"] == "task":
                self.assertIn(f"| {prompt['short']} |", doc, f"missing table row for {prompt['id']}")
        self.assertEqual(21, doc.count("\n| "), "scenario table header + rows")

    def test_doc_has_usage_and_preambles(self) -> None:
        doc = DOC.read_text(encoding="utf-8")
        self.assertIn("一条命令拿提示词", doc)
        self.assertIn("harness-prompt copy", doc)
        self.assertIn("### 0A. 已接入项目", doc)
        self.assertIn("### 0B. 未接入项目", doc)
        self.assertNotIn("{{", doc)

    def test_render_detects_drift_and_bad_placeholders(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            kit_copy = Path(tmp) / "kit"
            shutil.copytree(KIT, kit_copy)
            with (kit_copy / "prompts" / "fix-bug.md").open("a", encoding="utf-8") as handle:
                handle.write("\n多了一行\n")
            drift = subprocess.run(
                [sys.executable, str(kit_copy / "scripts" / "harness-prompt"), "render", "--check"],
                capture_output=True, text=True,
            )
            self.assertEqual(1, drift.returncode)
            self.assertIn("不一致", drift.stderr)

        with tempfile.TemporaryDirectory() as tmp:
            kit_copy = Path(tmp) / "kit"
            shutil.copytree(KIT, kit_copy)
            with (kit_copy / "prompts" / "fix-bug.md").open("a", encoding="utf-8") as handle:
                handle.write("\n{{UNDECLARED}}\n")
            bad = subprocess.run(
                [sys.executable, str(kit_copy / "scripts" / "harness-prompt"), "render", "--check"],
                capture_output=True, text=True,
            )
            self.assertEqual(1, bad.returncode)
            self.assertIn("placeholders", bad.stderr)


class PromptCliTests(unittest.TestCase):
    """`list` / `show` / `copy` behavior (the user-facing convenience path)."""

    def test_list_json_inventory(self) -> None:
        inventory = json.loads(run_prompt(["list", "--json"]).stdout)
        prompts = inventory["prompts"]
        by_id = {prompt["id"]: prompt for prompt in prompts}
        self.assertEqual(21, len(prompts))
        self.assertEqual(19, sum(1 for prompt in prompts if prompt["kind"] == "task"))
        self.assertEqual(2, sum(1 for prompt in prompts if prompt["kind"] == "addon"))
        self.assertEqual(2, sum(1 for prompt in prompts if prompt["stage"] == "unadopted"))
        self.assertEqual(17, sum(1 for prompt in prompts if prompt["stage"] == "adopted"))
        self.assertEqual("adopt-brownfield", prompts[1]["id"])

    def test_list_grouped_and_filtered(self) -> None:
        everything = run_prompt(["list"])
        self.assertEqual(0, everything.returncode, everything.stderr)
        for group in ("接入与接手", "评审与发布", "协作与收尾", "附加片段"):
            self.assertIn(group, everything.stdout)
        for prompt_id in ("adopt-new", "fix-bug", "completion-claim"):
            self.assertIn(prompt_id, everything.stdout)
        unadopted = run_prompt(["list", "--stage", "unadopted"])
        self.assertIn("adopt-brownfield", unadopted.stdout)
        self.assertNotIn("fix-bug", unadopted.stdout)
        addons = run_prompt(["list", "--stage", "addon"])
        self.assertIn("completion-claim", addons.stdout)
        self.assertNotIn("fix-bug", addons.stdout)

    def test_show_composes_preamble_by_stage(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp).resolve()
            unadopted = run_prompt(["show", "adopt-brownfield", "--target", str(target)])
            self.assertEqual(0, unadopted.returncode, unadopted.stderr)
            self.assertIn("未接入项目（接入阶段）", unadopted.stdout)
            self.assertIn(str(KIT.resolve()), unadopted.stdout)
            self.assertIn(str(target), unadopted.stdout)
            self.assertIn("harness-adopt", unadopted.stdout)
            self.assertNotIn("{{", unadopted.stdout)

            adopted = run_prompt(["show", "fix-bug", "--target", str(target)])
            self.assertEqual(0, adopted.returncode, adopted.stderr)
            self.assertIn("已接入项目", adopted.stdout)
            self.assertNotIn("未接入项目（接入阶段）", adopted.stdout)

            addon = run_prompt(["show", "completion-claim"])
            self.assertEqual(0, addon.returncode, addon.stderr)
            self.assertNotIn("前置｜", addon.stdout)
            self.assertIn("声明前：跑 make verify-static", addon.stdout)

    def test_show_flags_and_fills_placeholders(self) -> None:
        missing = run_prompt(["show", "fix-bug"])
        self.assertIn("<SYMPTOM>", missing.stdout)
        self.assertIn("<REPRO>", missing.stdout)
        self.assertIn("需要你补充", missing.stderr)
        filled = run_prompt(["show", "fix-bug", "--set", "SYMPTOM=登录后闪退", "--set", "REPRO=打开设置即退"])
        self.assertEqual(0, filled.returncode, filled.stderr)
        self.assertIn("登录后闪退", filled.stdout)
        self.assertNotIn("<SYMPTOM>", filled.stdout)
        self.assertNotIn("需要你补充", filled.stderr)

    def test_show_unknown_id_fails(self) -> None:
        process = run_prompt(["show", "no-such-prompt"])
        self.assertEqual(1, process.returncode)
        self.assertIn("unknown prompt id", process.stderr)
        self.assertIn("adopt-brownfield", process.stderr)

    @unittest.skipIf(os.name == "nt", "fake clipboard shim is POSIX-only")
    def test_copy_uses_clipboard(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            bindir = tmp_path / "bin"
            bindir.mkdir()
            output = tmp_path / "clipboard.txt"
            shim = bindir / "pbcopy"
            shim.write_text('#!/bin/sh\ncat > "$HARNESS_PROMPT_TEST_OUT"\n', encoding="utf-8")
            shim.chmod(0o755)
            env = dict(os.environ)
            env["PATH"] = f"{bindir}{os.pathsep}{env.get('PATH', '')}"
            env["HARNESS_PROMPT_TEST_OUT"] = str(output)
            process = run_prompt(["copy", "adopt-new", "--target", str(tmp_path)], env=env)
            self.assertEqual(0, process.returncode, process.stderr)
            self.assertIn("[OK] 已复制", process.stdout)
            self.assertIn(str(tmp_path), process.stdout)
            copied = output.read_text(encoding="utf-8")
            self.assertIn("未接入项目（接入阶段）", copied)
            self.assertIn("harness-init", copied)

    def test_copy_falls_back_to_stdout(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            empty_path = Path(tmp) / "empty-bin"
            empty_path.mkdir()
            env = dict(os.environ)
            env["PATH"] = str(empty_path)
            process = run_prompt(["copy", "completion-claim"], env=env)
            self.assertEqual(0, process.returncode, process.stderr)
            self.assertIn("声明前", process.stdout)
            self.assertIn("未找到可用的剪贴板命令", process.stderr)

    def test_list_reports_target_stage(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = make_adopted_target(Path(tmp) / "project")
            inventory = json.loads(run_prompt(["list", "--json", "--target", str(target)]).stdout)
            self.assertEqual("adopted", inventory["targetStage"])
            unadopted = json.loads(run_prompt(["list", "--json", "--target", tmp]).stdout)
            self.assertEqual("unadopted", unadopted["targetStage"])

    def test_show_warns_on_stage_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            empty = Path(tmp) / "empty"
            empty.mkdir()
            unadopted = run_prompt(["show", "fix-bug", "--target", str(empty)])
            self.assertEqual(0, unadopted.returncode)
            self.assertIn("看起来未接入", unadopted.stderr)
            adopted = make_adopted_target(Path(tmp) / "adopted")
            adopted_warning = run_prompt(["show", "adopt-new", "--target", str(adopted)])
            self.assertEqual(0, adopted_warning.returncode)
            self.assertIn("看起来已接入", adopted_warning.stderr)

    def test_show_warns_when_target_is_kit_dir(self) -> None:
        process = run_prompt(["show", "fix-bug"])
        self.assertEqual(0, process.returncode)
        self.assertIn("kit 克隆目录", process.stderr)

    def test_show_has_no_undeclared_angle_tokens(self) -> None:
        inventory = json.loads(run_prompt(["list", "--json"]).stdout)
        with tempfile.TemporaryDirectory() as tmp:
            adopted = make_adopted_target(Path(tmp) / "adopted")
            empty = Path(tmp) / "empty"
            empty.mkdir()
            for prompt in inventory["prompts"]:
                target = adopted if prompt["stage"] == "adopted" else empty
                if prompt["kind"] == "addon":
                    target = adopted
                process = run_prompt(["show", prompt["id"], "--target", str(target)])
                self.assertEqual(0, process.returncode, process.stderr)
                self.assertNotIn("{{", process.stdout)
                allowed = {f"<{key}>" for key in prompt["placeholders"]}
                found = [
                    match.group(0) for match in ANGLE_TOKEN_RE.finditer(process.stdout)
                    if match.group(0) not in allowed
                ]
                self.assertEqual([], found, f"{prompt['id']} has undeclared angle tokens")

    def test_render_writes_output_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "prompts-rendered.md"
            process = run_prompt(["render", "--output", str(output)])
            self.assertEqual(0, process.returncode, process.stderr)
            self.assertEqual(DOC.read_text(encoding="utf-8"), output.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
