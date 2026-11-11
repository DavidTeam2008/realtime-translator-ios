#!/usr/bin/env python3
"""JUnit XML → harness evidence payload adapter (standard library only; no network).

Usage:
    python3 tools/evidence_from_junit.py --xml GLOB [--xml GLOB ...] \
        --command "CMD" [--claim NAME] [--environment K=V ...] \
        [--notes TEXT] [--output PATH] \
        [--keep-raw] [--allow-outside-root] [--artifacts-dir PATH] [--root PATH]

Aggregates one or more JUnit XML reports (`testsuites` / `testsuite` / `testcase`)
and prints (or writes) a JSON payload accepted by
`tools/evidence.py write --from-json`:

    {
      "schemaVersion": 1,
      "claim": "tests-pass",
      "command": "make test",
      "environment": {"source": "junit-xml"},
      "result": {
        "status": "SUCCEEDED|FAILED",
        "passed": 12, "failed": 1, "skipped": 2, "durationSec": 3.14,
        "artifacts": ["harness/evidence/artifacts/20260101T000000Z-1-TEST-x.xml"],
        "artifactMode": "sanitized-copy"
      },
      "verdict": "PASS|FAIL",
      "verifier": "tools/evidence_from_junit.py"
    }

Artifact modes:
  - Default (sanitized-copy): each input XML is copied into the artifacts directory
    (`<paths.evidence>/artifacts` by default; fallback `harness/evidence/artifacts`).
    The copy removes `system-out` / `system-err` elements and `hostname` attributes,
    drops `<property>` entries whose name/value contains a local path or the hostname,
    and rewrites absolute repository/home paths (`<repo>` → relative, `$HOME`).
    Sanitization also covers `failure`/`error` `message`/`type`, testcase
    `classname`/`file` attributes and element text (hostname → `$HOST`); the sanitized
    tree is re-counted and a counts mismatch is rejected (anti-corruption). Inputs and
    `--artifacts-dir` symlinks are rejected; artifacts are written to a temp file and
    moved with `os.replace` (atomic). `result.artifacts` holds repository-relative paths
    and `result.artifactMode` is `sanitized-copy`. Input or sanitized output larger than
    5 MiB is rejected (exit 2).
  - `--keep-raw`: keeps the previous behavior (no sanitization, no copy); artifacts are
    the input paths as given. Inputs outside the repository require an explicit
    `--allow-outside-root` (otherwise exit 2 with a hint to use the default mode);
    even then a warning is printed and `notes` records that `verify_claim` will mark
    the evidence UNVERIFIED (absolute artifact, CI cannot recheck). `--artifacts-dir`
    must stay inside `--root`; `--environment` values that look like a local path / IP /
    hostname only produce a privacy WARNING (they are still written into the JSON).
    `result.artifactMode` is `raw`.

Counting rules:
  - tests   = <testcase> elements (a <testsuite> with no testcase children falls
              back to its `tests` attribute);
  - failed  = <failure> + <error> child elements (a test with both counts twice);
  - skipped = <skipped> child elements;
  - passed  = max(0, tests - failed - skipped);
  - status  = SUCCEEDED when failed == 0 else FAILED (skips are expected);
  - verdict = PASS when failed == 0 else FAIL;
  - durationSec = sum of testcase `time` attributes; when a suite's testcases
              carry no `time` attribute (or the suite has no testcase children),
              the testsuite `time` attribute is used instead (rounded to 3 decimals).

`--xml` patterns may be files, directories (searched recursively for `*.xml`) or
globs, resolved relative to `--root` (default: script parent parent). Every
pattern must match at least one `*.xml` file. `--output` is also relative to
`--root` when relative. Hit content is not interpreted: this adapter only counts.

Exit codes: 0 = payload produced; 2 = usage error / missing or malformed XML /
oversized artifact / unsafe raw input.
No third-party dependencies, no network; only `--output` and sanitized copies are written.
"""
from __future__ import annotations

import argparse
import copy
import glob
import json
import os
import re
import sys
import tempfile
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_CLAIM = "tests-pass"
VERIFIER = "tools/evidence_from_junit.py"
MAX_ARTIFACT_BYTES = 5 * 1024 * 1024
ARTIFACTS_DIRNAME = "artifacts"
MODE_SANITIZED = "sanitized-copy"
MODE_RAW = "raw"
REMOVED_ELEMENTS = ("system-out", "system-err")
# Privacy hints for --environment KEY=VALUE (warn only; the value still goes into the JSON).
IPV4_RE = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
LOCAL_PATH_HINT_RE = re.compile("/" + "(?:Users|Volumes|home)" + "/")


class JUnitError(Exception):
    """User-facing failure (exit 2)."""


@dataclass
class Counts:
    """Aggregated JUnit counters."""

    tests: int = 0
    failed: int = 0
    skipped: int = 0
    duration: float = 0.0


def local_name(tag: str) -> str:
    """Strip an XML namespace from a tag name."""
    return tag.rsplit("}", 1)[-1] if "}" in tag else tag


def as_int(value: object, default: int = 0) -> int:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return default


def as_float(value: object, default: float = 0.0) -> float:
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        return default


def display(root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def count_case(element: ET.Element, counts: Counts) -> None:
    counts.tests += 1
    counts.duration += as_float(element.get("time"))
    for child in element:
        name = local_name(child.tag)
        if name in ("failure", "error"):
            counts.failed += 1
        elif name == "skipped":
            counts.skipped += 1


def count_suite(suite: ET.Element, counts: Counts) -> None:
    cases = [child for child in suite if local_name(child.tag) == "testcase"]
    if cases:
        has_case_time = any(case.get("time") is not None for case in cases)
        for case in cases:
            count_case(case, counts)
        if not has_case_time:
            # Reporters that keep the duration only at suite level.
            counts.duration += as_float(suite.get("time"))
        return
    # Report-only suite (no testcase children): trust the aggregation attributes.
    counts.tests += as_int(suite.get("tests"))
    counts.failed += as_int(suite.get("failures")) + as_int(suite.get("errors"))
    counts.skipped += as_int(suite.get("skipped"))
    counts.duration += as_float(suite.get("time"))


def aggregate(root: ET.Element) -> Counts:
    """Aggregate one parsed JUnit document; tolerates testsuites/testsuite/testcase roots."""
    counts = Counts()
    tag = local_name(root.tag)
    if tag == "testcase":
        count_case(root, counts)
        return counts
    if tag == "testsuite":
        count_suite(root, counts)
        return counts
    suites = [child for child in root if local_name(child.tag) == "testsuite"]
    if not suites:
        suites = [element for element in root.iter() if local_name(element.tag) == "testsuite"]
    if suites:
        for suite in suites:
            count_suite(suite, counts)
        return counts
    # Unknown wrapper without suites: treat it as an attribute-only suite container.
    count_suite(root, counts)
    return counts


# ── sanitize-copy helpers ────────────────────────────────────────────────
def project_hostname() -> str:
    import socket

    try:
        return socket.gethostname().strip()
    except OSError:  # pragma: no cover - defensive
        return ""


def load_paths_config(root: Path) -> dict:
    try:
        config = json.loads((root / "harness" / "config.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return config if isinstance(config, dict) else {}


def default_artifacts_dir(root: Path) -> Path:
    config = load_paths_config(root)
    paths = config.get("paths") if isinstance(config.get("paths"), dict) else {}
    evidence_rel = paths.get("evidence") if isinstance(paths.get("evidence"), str) else ""
    if evidence_rel.strip():
        return root / evidence_rel.strip() / ARTIFACTS_DIRNAME
    return root / "harness" / "evidence" / ARTIFACTS_DIRNAME


def resolve_artifacts_dir(root: Path, value: str | None) -> Path:
    raw = Path(value).expanduser() if value else default_artifacts_dir(root)
    candidate = raw if raw.is_absolute() else root / raw
    if candidate.is_symlink():
        raise JUnitError(f"--artifacts-dir 不能是符号链接：{candidate}")
    resolved = candidate.resolve()
    try:
        resolved.relative_to(root.resolve())
    except ValueError:
        raise JUnitError(
            f"--artifacts-dir 必须在仓库内（result.artifacts 需要仓库相对路径）：{resolved}"
        ) from None
    return resolved


def path_variants(value: str) -> list[str]:
    """A path in both separator styles, with and without a trailing separator."""
    if not value:
        return []
    forward = value.rstrip("/\\")
    backward = forward.replace("/", "\\")
    variants = [forward, forward + "/", forward + "\\"]
    if backward != forward:
        variants.extend([backward, backward + "\\"])
    return variants


def sanitize_substitutions(root: Path, extra_roots: list[Path] | None = None) -> list[tuple[str, str]]:
    """Root/home path substitutions; extra_roots keeps unresolved --root spellings working."""
    home = str(Path.home())
    substitutions: list[tuple[str, str]] = []
    roots = [root]
    for extra in extra_roots or []:
        if str(extra) not in {str(candidate) for candidate in roots}:
            roots.append(extra)
    for candidate in roots:
        for variant in path_variants(str(candidate)):
            substitutions.append((variant, ""))
        for variant in path_variants(str(candidate.resolve())):
            substitutions.append((variant, ""))
    for variant in path_variants(home):
        replacement = "$HOME/" if variant.endswith(("/", "\\")) else "$HOME"
        substitutions.append((variant, replacement))
    hostname = project_hostname()
    if hostname:
        substitutions.append((hostname, "$HOST"))
        if hostname.lower() != hostname:
            substitutions.append((hostname.lower(), "$HOST"))
    # Longest needle first so nested paths are rewritten before their parents.
    deduped: list[tuple[str, str]] = []
    seen: set[str] = set()
    for needle, replacement in sorted(substitutions, key=lambda item: len(item[0]), reverse=True):
        if needle in seen:
            continue
        seen.add(needle)
        deduped.append((needle, replacement))
    return deduped


def normalize_separators(text: str) -> str:
    return text.replace("\\", "/")


def hits_local_path(text: str, substitutions: list[tuple[str, str]], hostname: str) -> bool:
    if hostname and hostname.lower() in text.lower():
        return True
    normalized = normalize_separators(text)
    for needle, _replacement in substitutions:
        candidate = normalize_separators(needle).rstrip("/")
        if candidate and candidate in normalized:
            return True
    return False


def sanitize_text(text: str, substitutions: list[tuple[str, str]]) -> str:
    result = text
    for needle, replacement in substitutions:
        result = result.replace(needle, replacement)
    return result


def sanitize_element(element: ET.Element, substitutions: list[tuple[str, str]], hostname: str) -> ET.Element:
    # 1) drop system-out / system-err anywhere in the tree.
    for parent in list(element.iter()):
        for child in list(parent):
            if local_name(child.tag) in REMOVED_ELEMENTS:
                parent.remove(child)
    # 2) drop hostname attributes.
    for node in element.iter():
        for key in list(node.attrib):
            if key.lower() == "hostname":
                del node.attrib[key]
    # 3) drop properties whose name/value leaks a local path or the hostname.
    for parent in list(element.iter()):
        for child in list(parent):
            if local_name(child.tag) != "property":
                continue
            name = child.get("name") or ""
            value = child.get("value") or ""
            if hits_local_path(f"{name} {value}", substitutions, hostname):
                parent.remove(child)
    # 4) rewrite remaining absolute repo/home paths everywhere.
    for node in element.iter():
        for key, value in list(node.attrib.items()):
            node.set(key, sanitize_text(value, substitutions))
        if node.text:
            node.text = sanitize_text(node.text, substitutions)
        if node.tail:
            node.tail = sanitize_text(node.tail, substitutions)
    return element


def unique_artifact_path(directory: Path, name: str) -> Path:
    candidate = directory / name
    if not candidate.exists():
        return candidate
    stem = Path(name).stem
    index = 2
    while True:
        candidate = directory / f"{stem}-{index}.xml"
        if not candidate.exists():
            return candidate
        index += 1


def _counts_tuple(counts: Counts) -> tuple[int, int, int]:
    return counts.tests, counts.failed, counts.skipped


def write_sanitized_artifacts(
    root: Path,
    artifacts_dir: Path,
    parsed: list[tuple[Path, ET.Element]],
    original_counts: list[Counts],
    *,
    utc: str,
    extra_roots: list[Path] | None = None,
) -> list[str]:
    substitutions = sanitize_substitutions(root, extra_roots)
    hostname = project_hostname()
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    written: list[str] = []
    for index, (original, element) in enumerate(parsed, start=1):
        sanitized = sanitize_element(copy.deepcopy(element), substitutions, hostname)
        sanitized_counts = aggregate(sanitized)
        if _counts_tuple(sanitized_counts) != _counts_tuple(original_counts[index - 1]):
            raise JUnitError(
                "脱敏后计数与原始 JUnit 不一致，拒绝写入："
                f"{original.name}（原始 {_counts_tuple(original_counts[index - 1])} / "
                f"脱敏 {_counts_tuple(sanitized_counts)}）；请检查 sanitize 规则"
            )
        payload = ET.tostring(sanitized, encoding="utf-8", xml_declaration=True)
        if len(payload) > MAX_ARTIFACT_BYTES:
            raise JUnitError(
                f"脱敏后 artifact 超过 5 MiB：{original.name}（{len(payload)} bytes）；"
                "请拆分报告或使用 --keep-raw 并自行清理"
            )
        target = unique_artifact_path(artifacts_dir, f"{utc}-{index}-{original.stem}.xml")
        temp_name = ""
        try:
            handle, temp_name = tempfile.mkstemp(
                prefix=".artifact-", suffix=".tmp", dir=str(artifacts_dir)
            )
            os.close(handle)
            Path(temp_name).write_bytes(payload)
            os.replace(temp_name, target)
            temp_name = ""
        except OSError as exc:
            raise JUnitError(f"脱敏 artifact 写入失败：{display(root, target)}：{exc}") from exc
        finally:
            if temp_name and os.path.exists(temp_name):
                try:
                    os.unlink(temp_name)
                except OSError:  # pragma: no cover - 尽力清理
                    pass
        written.append(display(root, target))
    return written


def is_inside_root(root: Path, path: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


# ── pattern / environment parsing ────────────────────────────────────────
def resolve_xml_patterns(root: Path, patterns: list[str]) -> tuple[list[Path], list[str]]:
    """Expand --xml file/dir/glob patterns into a de-duplicated, sorted file list."""
    files: list[Path] = []
    problems: list[str] = []
    seen: set[Path] = set()
    for pattern in patterns:
        candidate = Path(pattern).expanduser()
        search = str(candidate if candidate.is_absolute() else root / candidate)
        matches = sorted(glob.glob(search, recursive=True))
        found: list[Path] = []
        for match in matches:
            path = Path(match)
            if path.is_symlink():
                problems.append(f"输入 JUnit XML 不能是符号链接：{display(root, path)}")
                continue
            if path.is_dir():
                for child in sorted(path.rglob("*.xml")):
                    if child.is_symlink():
                        problems.append(f"输入 JUnit XML 不能是符号链接：{display(root, child)}")
                        continue
                    found.append(child)
            elif path.is_file() and path.suffix.lower() == ".xml":
                found.append(path)
        if not found:
            problems.append(f"--xml 模式未匹配到 XML 文件：{pattern}")
            continue
        for path in found:
            resolved = path.resolve()
            if resolved not in seen:
                seen.add(resolved)
                files.append(resolved)
    if not patterns:
        problems.append("至少需要一个 --xml GLOB")
    return files, problems


def parse_environment(
    root: Path,
    pairs: list[str],
    warnings: list[str] | None = None,
    extra_roots: list[Path] | None = None,
) -> dict[str, str]:
    environment: dict[str, str] = {}
    hostname = project_hostname()
    home = str(Path.home())
    roots = [root, *(extra_roots or [])]
    root_paths = {str(candidate) for candidate in roots}
    root_paths.update({str(candidate.resolve()) for candidate in roots})
    for pair in pairs:
        if "=" not in pair:
            raise JUnitError(f"--environment 需要 KEY=VALUE 形式：{pair!r}")
        key, value = pair.split("=", 1)
        key = key.strip()
        if not key:
            raise JUnitError(f"--environment 的 KEY 不能为空：{pair!r}")
        suspicious = bool(
            IPV4_RE.search(value)
            or LOCAL_PATH_HINT_RE.search(value)
            or (hostname and hostname in value)
            or (home and home in value)
            or any(path in value for path in root_paths if path)
        )
        if suspicious and warnings is not None:
            warnings.append(
                f"--environment {key} 的值疑似本机路径/IP/hostname（会写入证据 JSON，注意隐私）：{value}"
            )
        environment[key] = value
    return environment or {"source": "junit-xml"}


# ── payload ──────────────────────────────────────────────────────────────
def parse_inputs(root: Path, files: list[Path]) -> list[tuple[Path, ET.Element]]:
    parsed: list[tuple[Path, ET.Element]] = []
    for path in files:
        if path.is_symlink():
            raise JUnitError(f"输入 JUnit XML 不能是符号链接：{display(root, path)}")
        try:
            size = path.stat().st_size
        except OSError as exc:
            raise JUnitError(f"JUnit XML 无法读取：{display(root, path)}：{exc}") from exc
        if size > MAX_ARTIFACT_BYTES:
            raise JUnitError(
                f"输入 JUnit XML 超过 5 MiB：{display(root, path)}（{size} bytes）；"
                "请拆分报告或使用 --keep-raw 并自行清理"
            )
        try:
            element = ET.parse(path).getroot()
        except ET.ParseError as exc:
            raise JUnitError(f"JUnit XML 解析失败：{display(root, path)}：{exc}") from exc
        except OSError as exc:
            raise JUnitError(f"JUnit XML 无法读取：{display(root, path)}：{exc}") from exc
        parsed.append((path, element))
    return parsed


def build_payload(
    root: Path,
    parsed: list[tuple[Path, ET.Element]],
    claim: str,
    command: str,
    environment: dict[str, str],
    notes: str | None,
    *,
    keep_raw: bool = False,
    allow_outside_root: bool = False,
    artifacts_dir: str | None = None,
    extra_roots: list[Path] | None = None,
    warnings: list[str] | None = None,
) -> dict:
    totals = Counts()
    per_file_counts: list[Counts] = []
    for _path, element in parsed:
        counts = aggregate(element)
        per_file_counts.append(counts)
        totals.tests += counts.tests
        totals.failed += counts.failed
        totals.skipped += counts.skipped
        totals.duration += counts.duration
    passed = max(0, totals.tests - totals.failed - totals.skipped)
    files = [path for path, _element in parsed]

    if keep_raw:
        outside = [path for path in files if not is_inside_root(root, path)]
        if outside and not allow_outside_root:
            raise JUnitError(
                "--keep-raw 下输入 JUnit 在仓库外："
                + "、".join(display(root, path) for path in outside[:3])
                + "；请改用默认脱敏复制模式（会复制进仓库并脱敏），"
                "或显式 --allow-outside-root（artifacts 将保留绝对路径，CI 无法复核）"
            )
        artifacts = [display(root, path) for path in files]
        artifact_mode = MODE_RAW
        if outside:
            warning = (
                "artifact 是仓库外绝对路径，verify_claim 会判 UNVERIFIED："
                + "、".join(display(root, path) for path in outside[:3])
            )
            if warnings is not None:
                warnings.append(warning)
            suffix = "；artifact 为仓库外绝对路径，verify_claim 会判 UNVERIFIED"
            notes = f"{notes}{suffix}" if notes else suffix
    else:
        target_dir = resolve_artifacts_dir(root, artifacts_dir)
        utc = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        artifacts = write_sanitized_artifacts(
            root, target_dir, parsed, per_file_counts, utc=utc, extra_roots=extra_roots
        )
        artifact_mode = MODE_SANITIZED

    payload: dict = {
        "schemaVersion": 1,
        "claim": claim,
        "command": command,
        "environment": environment,
        "result": {
            "status": "SUCCEEDED" if totals.failed == 0 else "FAILED",
            "passed": passed,
            "failed": totals.failed,
            "skipped": totals.skipped,
            "durationSec": round(totals.duration, 3),
            "artifacts": artifacts,
            "artifactMode": artifact_mode,
        },
        "verdict": "PASS" if totals.failed == 0 else "FAIL",
        "verifier": VERIFIER,
    }
    if notes is not None:
        payload["notes"] = notes
    return payload


# ── CLI ──────────────────────────────────────────────────────────────────
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Aggregate JUnit XML into a harness evidence payload (JSON). "
            "By default artifacts are sanitized and copied into the repository."
        ),
    )
    parser.add_argument(
        "--xml",
        action="append",
        required=True,
        metavar="GLOB",
        help="JUnit XML file/directory/glob, relative to --root (repeatable)",
    )
    parser.add_argument("--claim", default=DEFAULT_CLAIM, help=f"claim name (default: {DEFAULT_CLAIM})")
    parser.add_argument("--command", required=True, help="command that produced these reports")
    parser.add_argument(
        "--environment",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help="environment entry for the evidence record (repeatable; e.g. id=server os=linux python=3.12)",
    )
    parser.add_argument("--notes", help="free-form notes stored in the evidence record")
    parser.add_argument("--output", metavar="PATH", help="write JSON here (default: stdout)")
    parser.add_argument(
        "--keep-raw",
        action="store_true",
        help="keep legacy behavior: do not sanitize/copy artifacts (requires --allow-outside-root for outside inputs)",
    )
    parser.add_argument(
        "--allow-outside-root",
        action="store_true",
        help="with --keep-raw: allow input reports outside the repository (artifacts stay absolute; CI cannot recheck)",
    )
    parser.add_argument(
        "--artifacts-dir",
        metavar="PATH",
        help="sanitized artifact directory (default: <paths.evidence>/artifacts; must be inside --root)",
    )
    parser.add_argument(
        "--root",
        default=str(Path(__file__).resolve().parent.parent),
        help="project root for relative paths (default: script parent parent)",
    )
    return parser


def fail(message: str) -> int:
    print(f"[FAIL] {message}", file=sys.stderr)
    return 2


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root_arg = Path(args.root).expanduser()
    root = root_arg.resolve()
    if not root.is_dir():
        return fail(f"--root 目录不存在：{root}")
    command = args.command.strip()
    if not command:
        return fail("--command 不能为空（写入证据 provenance 的测试命令）")
    if not args.claim.strip():
        return fail("--claim 不能为空")

    files, problems = resolve_xml_patterns(root, args.xml)
    if problems:
        for problem in problems:
            print(f"[FAIL] {problem}", file=sys.stderr)
        return 2
    warnings: list[str] = []
    try:
        parsed = parse_inputs(root, files)
        environment = parse_environment(root, args.environment, warnings, extra_roots=[root_arg])
        payload = build_payload(
            root,
            parsed,
            args.claim.strip(),
            command,
            environment,
            args.notes,
            keep_raw=args.keep_raw,
            allow_outside_root=args.allow_outside_root,
            artifacts_dir=args.artifacts_dir,
            extra_roots=[root_arg],
            warnings=warnings,
        )
    except JUnitError as exc:
        return fail(str(exc))

    for warning in warnings:
        print(f"[WARN] {warning}", file=sys.stderr)
    text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        output = Path(args.output).expanduser()
        if not output.is_absolute():
            output = root / output
        try:
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(text, encoding="utf-8")
        except OSError as exc:
            return fail(f"--output 写入失败：{output}：{exc}")
        result = payload["result"]
        print(
            f"[OK] wrote {display(root, output.resolve())} "
            f"(mode={result['artifactMode']} tests={result['status']} "
            f"passed={result['passed']} failed={result['failed']} skipped={result['skipped']})"
        )
        return 0
    sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
