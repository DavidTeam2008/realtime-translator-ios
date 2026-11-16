#!/usr/bin/env python3
"""kit-resolve: locate (and if needed bootstrap) the harness-kit the skill runs against.

The entry skill is installed by `npx skills add ...` or by `<kit>/scripts/harness-skill`
without necessarily having a kit clone on the machine. This script is the only
networking entry point of the skill: it resolves a kit root from local sources
first and only clones the official mirror (pinned annotated tag) into a user
cache when nothing local matches.

Resolution order:
  1. explicit `--kit-root` / `HARNESS_KIT_ROOT`
  2. embedded `harness-kit/VERSION` in the target repo or an ancestor (project pin)
  3. adopted repo fast path (target has `tools/harness.py`): no kit required, no network
  4. npx-managed install: skills lock entry -> ignore legacy skill metadata
     (otherwise) legacy user metadata `~/.agents/skills/.harness-kit-skill.json` kitRoot
  5. cache: $HARNESS_KIT_CACHE / $XDG_CACHE_HOME/harness-kit / ~/.cache/harness-kit,
     keyed by repo URL + tag; verified locally (marker + VERSION + HEAD), no network
  6. clone `--repo-url` (default: SKILL.md metadata kit_repo) at tag `v<kit_version>`,
     require an annotated tag and HEAD == peeled tag commit, then atomic rename.

Exit codes: 0 resolved (including adopted repositories with kitRoot=null);
2 usage error / kit too old / offline without a local kit / clone or tag
verification failure.

Standard library only; no secrets are read.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
SKILL_MD = SKILL_DIR / "SKILL.md"
MARKER_NAME = ".harness-kit-cache.json"
DEFAULT_REPO = "https://github.com/DavidTeam2008/harness-engineering-kit.git"
CANONICAL_HINT = "harness-engineering-kit"
TIMEOUT = 180


class ResolveError(Exception):
    """User-facing failure (exit 2)."""


def read_metadata() -> dict[str, str]:
    text = SKILL_MD.read_text(encoding="utf-8")
    if not text.startswith("---"):
        raise ResolveError(f"SKILL.md 缺少 front matter：{SKILL_MD}")
    front = text.split("---", 2)[1]
    meta: dict[str, str] = {}
    for key in ("kit_version", "min_version", "kit_repo", "kit"):
        match = re.search(rf"{key}:\s*([^,\n}}]+)", front)
        if match:
            meta[key] = match.group(1).strip().strip("'\"")
    for required in ("kit_version", "min_version"):
        if not meta.get(required):
            raise ResolveError(f"SKILL.md metadata 缺少 {required}：{SKILL_MD}")
    return meta


def version_tuple(value: str) -> tuple[int, ...]:
    match = re.match(r"^(\d+(?:\.\d+)*)", value)
    if not match:
        raise ResolveError(f"无法解析版本号：{value}")
    return tuple(int(part) for part in match.group(1).split("."))


def compare(left: str, right: str) -> int:
    a, b = version_tuple(left), version_tuple(right)
    width = max(len(a), len(b))
    a += (0,) * (width - len(a))
    b += (0,) * (width - len(b))
    return (a > b) - (a < b)


def kit_version_of(root: Path) -> str | None:
    path = root / "VERSION"
    if not path.is_file():
        return None
    return path.read_text(encoding="utf-8").strip()


def version_status(version: str, expected: str) -> str:
    if version == expected:
        return "ok"
    return "older-than-skill" if compare(version, expected) < 0 else "newer-than-skill"


def validate_kit(root: Path, expected: str, minimum: str, source: str,
                 warnings: list[str]) -> dict:
    version = kit_version_of(root)
    if version is None:
        raise ResolveError(f"kit root 缺少 VERSION：{root}")
    if compare(version, minimum) < 0:
        raise ResolveError(
            f"kit 版本 {version} 低于 skill 要求的最低版本 {minimum}（{root}）；"
            "请升级 kit 或重装 skill"
        )
    status = version_status(version, expected)
    if status != "ok":
        warnings.append(
            f"kit {version} 与 skill 期望 {expected} 不一致（{source}）；"
            f"{'建议升级 kit' if status == 'older-than-skill' else 'skill 可升级'}"
        )
    return {"kitRoot": root.as_posix(), "version": version, "versionStatus": status,
            "source": source}


def find_embedded(target: Path) -> Path | None:
    current = target.resolve()
    for directory in (current, *current.parents):
        candidate = directory / "harness-kit"
        if kit_version_of(candidate):
            return candidate
    return None


def home_path(env_name: str, fallback: str) -> Path:
    raw = os.environ.get(env_name)
    return Path(raw).expanduser() if raw else Path.home() / fallback


def legacy_meta_path() -> Path:
    return home_path("DSH_AGENTS_HOME", ".agents") / "skills" / ".harness-kit-skill.json"


def skills_lock_paths() -> list[Path]:
    paths: list[Path] = []
    state = os.environ.get("XDG_STATE_HOME")
    if state:
        paths.append(Path(state).expanduser() / "skills" / ".skill-lock.json")
    paths.append(home_path("DSH_AGENTS_HOME", ".agents") / ".skill-lock.json")
    return paths


def read_json(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def npx_managed() -> bool:
    for path in skills_lock_paths():
        entry = read_json(path).get("skills", {})
        item = entry.get("harness") if isinstance(entry, dict) else None
        if not isinstance(item, dict):
            continue
        source = str(item.get("source") or item.get("sourceUrl") or "")
        if CANONICAL_HINT in source:
            return True
    return False


def cache_root() -> Path:
    raw = os.environ.get("HARNESS_KIT_CACHE")
    if raw:
        return Path(raw).expanduser()
    xdg = os.environ.get("XDG_CACHE_HOME")
    if xdg:
        return Path(xdg).expanduser() / "harness-kit"
    return Path.home() / ".cache" / "harness-kit"


def repo_key(repo_url: str) -> str:
    normalized = repo_url.rstrip("/")
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:12]


def git(args: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    env["GIT_TERMINAL_PROMPT"] = "0"
    try:
        return subprocess.run(["git", *args], cwd=str(cwd) if cwd else None,
                              capture_output=True, text=True, timeout=TIMEOUT, env=env)
    except FileNotFoundError as exc:  # pragma: no cover - environment guard
        raise ResolveError(f"未找到 git（自动 clone kit 需要 git）：{exc}") from exc
    except subprocess.TimeoutExpired as exc:
        raise ResolveError(f"git 超时（{TIMEOUT}s）：git {' '.join(args)}") from exc


def peeled_tag_commit(repo_url: str, tag: str) -> str:
    proc = git(["ls-remote", "--tags", repo_url, f"refs/tags/{tag}", f"refs/tags/{tag}^{{}}"])
    if proc.returncode != 0:
        raise ResolveError(
            f"无法读取远程 tag {tag}（{repo_url}）：{(proc.stderr or proc.stdout).strip()[:500]}"
        )
    peeled = None
    found = False
    for line in proc.stdout.splitlines():
        parts = line.split()
        if len(parts) != 2:
            continue
        sha, ref = parts
        found = True
        if ref.endswith("^{}"):
            peeled = sha
    if not found:
        raise ResolveError(
            f"镜像仓没有 tag {tag}（{repo_url}）；可能发布尚未完成。"
            "离线环境请手动 clone 并设置 HARNESS_KIT_ROOT"
        )
    if peeled is None:
        raise ResolveError(
            f"tag {tag} 是轻量 tag；kit 发布要求 annotated tag（无法校验 commit sha）。"
            "请升级 kit 或用 --repo-url 指向含 annotated tag 的仓库"
        )
    return peeled


def cache_valid(path: Path, repo_url: str, expected: str) -> bool:
    """Local-only cache check: marker + VERSION + HEAD == marker commit (no network)."""
    if not path.is_dir():
        return False
    if kit_version_of(path) != expected:
        return False
    marker = read_json(path / MARKER_NAME)
    if marker.get("repoUrl") != repo_url or marker.get("version") != expected:
        return False
    head = git(["rev-parse", "HEAD"], cwd=path)
    return head.returncode == 0 and head.stdout.strip() == marker.get("commitSha")


def clone_into_cache(base: Path, repo_url: str, expected: str, cache_dir: Path,
                     refresh: bool, warnings: list[str]) -> dict:
    tag = f"v{expected}"
    commit = peeled_tag_commit(repo_url, tag)
    base.mkdir(parents=True, exist_ok=True)
    if refresh and cache_dir.exists():
        resolved = cache_dir.resolve()
        if base.resolve() not in resolved.parents:
            raise ResolveError(f"拒绝清理缓存目录之外的路径：{resolved}")
        shutil.rmtree(resolved)
    temp = Path(tempfile.mkdtemp(prefix=".clone-", dir=str(base)))
    try:
        checkout = temp / "kit"
        proc = git(["clone", "--depth", "1", "--branch", tag, repo_url, str(checkout)])
        if proc.returncode != 0:
            raise ResolveError(
                f"clone kit 失败（{repo_url} {tag}）：{(proc.stderr or proc.stdout).strip()[:500]}"
            )
        version = kit_version_of(checkout)
        if version != expected:
            raise ResolveError(
                f"clone 的 kit 版本 {version} 与期望 {expected} 不一致（{repo_url} {tag}）"
            )
        head = git(["rev-parse", "HEAD"], cwd=checkout)
        if head.returncode != 0 or head.stdout.strip() != commit:
            raise ResolveError(
                f"clone 的 HEAD 与 tag {tag} 的 commit 不一致（{head.stdout.strip() or head.stderr.strip()}）"
            )
        marker = {
            "repoUrl": repo_url,
            "version": expected,
            "tag": tag,
            "commitSha": commit,
            "clonedAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        (checkout / MARKER_NAME).write_text(
            json.dumps(marker, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        cache_dir.parent.mkdir(parents=True, exist_ok=True)
        if cache_dir.exists():
            if cache_valid(cache_dir, repo_url, expected):
                warnings.append(f"缓存目录已存在且校验通过，复用而非替换：{cache_dir}")
                shutil.rmtree(temp, ignore_errors=True)
            else:
                resolved = cache_dir.resolve()
                if base.resolve() not in resolved.parents:
                    raise ResolveError(f"拒绝清理缓存目录之外的路径：{resolved}")
                warnings.append(f"缓存校验失败，已重新 clone：{cache_dir}")
                shutil.rmtree(resolved)
                os.replace(checkout, cache_dir)
                shutil.rmtree(temp, ignore_errors=True)
        else:
            os.replace(checkout, cache_dir)
            shutil.rmtree(temp, ignore_errors=True)
    finally:
        if temp.exists():
            shutil.rmtree(temp, ignore_errors=True)
    return {"kitRoot": cache_dir.as_posix(), "version": expected, "versionStatus": "ok",
            "source": "clone", "commit": commit}


def resolve(args: argparse.Namespace) -> dict:
    meta = read_metadata()
    expected = meta["kit_version"]
    minimum = meta["min_version"]
    repo_url = (args.repo_url or os.environ.get("HARNESS_KIT_REPO")
                or meta.get("kit_repo") or DEFAULT_REPO)
    warnings: list[str] = []
    target = Path(args.target).expanduser()
    if not target.exists():
        raise ResolveError(f"--target 不存在：{target}")
    result: dict = {
        "kitRoot": None, "version": None, "versionExpected": expected,
        "versionMin": minimum, "versionStatus": "unknown", "source": "none",
        "adopted": False, "managedBy": "npx" if npx_managed() else None,
        "cacheHit": False, "cloned": False, "repoUrl": repo_url, "tag": None,
        "commit": None, "warnings": warnings,
    }
    if CANONICAL_HINT not in repo_url:
        warnings.append(f"非官方 repo-url（{repo_url}）；仅用于测试或镜像，请确认来源可信")

    explicit = args.kit_root or os.environ.get("HARNESS_KIT_ROOT")
    if explicit:
        resolved = validate_kit(Path(explicit).expanduser(), expected, minimum, "explicit", warnings)
        result.update(resolved)
        result["adopted"] = (target / "tools" / "harness.py").is_file()
        return result

    embedded = find_embedded(target)
    if embedded:
        result.update(validate_kit(embedded, expected, minimum, "embedded", warnings))
        result["adopted"] = (target / "tools" / "harness.py").is_file()
        return result

    adopted = (target / "tools" / "harness.py").is_file()
    result["adopted"] = adopted
    if adopted and not args.require_kit:
        return result

    if result["managedBy"] is None:
        meta_path = legacy_meta_path()
        meta_data = read_json(meta_path)
        legacy_root = meta_data.get("kitRoot")
        if legacy_root:
            candidate = Path(str(legacy_root)).expanduser()
            if kit_version_of(candidate):
                result.update(validate_kit(candidate, expected, minimum, "meta", warnings))
                return result
            warnings.append(f"旧用户级安装记录指向不存在的 kit，已忽略：{legacy_root}")
    elif legacy_meta_path().is_file():
        warnings.append(
            "检测到 npx 管理与旧 harness-skill 元数据共存：已按 npx 解析并忽略旧 kitRoot；"
            f"建议删除 {legacy_meta_path()}"
        )

    base = cache_root()
    cache_dir = base / repo_key(repo_url) / f"v{expected}"
    if not args.refresh and cache_valid(cache_dir, repo_url, expected):
        result.update({"kitRoot": cache_dir.as_posix(), "version": expected,
                       "versionStatus": "ok", "source": "cache", "cacheHit": True,
                       "commit": read_json(cache_dir / MARKER_NAME).get("commitSha")})
        return result
    if args.offline:
        raise ResolveError(
            "离线且没有可用的本地 kit（cache/meta/仓库内嵌均未命中）。手动路径：\n"
            f"  git clone --depth 1 --branch v{expected} {repo_url} <kit>\n"
            "  export HARNESS_KIT_ROOT=<kit>\n"
            "或使用 harness-skill（需要 kit 克隆）：<kit>/scripts/harness-skill install --scope user"
        )
    cloned = clone_into_cache(base, repo_url, expected, cache_dir, args.refresh, warnings)
    result.update(cloned)
    result.update({"cloned": True, "tag": f"v{expected}", "cacheHit": False})
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="定位（必要时自动 clone）skill 运行所需的 harness-kit")
    parser.add_argument("--target", default=".", help="目标仓库路径（默认当前目录）")
    parser.add_argument("--kit-root", help="显式 kit 路径（等价 HARNESS_KIT_ROOT）")
    parser.add_argument("--repo-url", help="kit 镜像仓 URL（默认取 SKILL.md metadata kit_repo）")
    parser.add_argument("--offline", action="store_true", help="禁止 clone（仅用本地来源）")
    parser.add_argument("--refresh", action="store_true", help="强制重新 clone 覆盖缓存")
    parser.add_argument("--require-kit", action="store_true",
                        help="已接入仓库也要求返回 kit（adopt / upgrade 场景）")
    parser.add_argument("--json", action="store_true", help="输出 JSON")
    args = parser.parse_args(argv)
    try:
        result = resolve(args)
    except ResolveError as exc:
        if args.json:
            print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False, indent=2))
        else:
            print(f"[FAIL] {exc}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    if result["adopted"]:
        print("adopted: 是（仓库自带 tools/harness.py，可直接 status，不需要 kit）")
    if result["kitRoot"]:
        print(f"kit root: {result['kitRoot']}")
        print(f"version: {result['version']}（期望 {result['versionExpected']}，"
              f"source={result['source']}）")
        if result.get("commit"):
            print(f"commit: {result['commit']}")
    for warning in result["warnings"]:
        print(f"[WARN] {warning}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
