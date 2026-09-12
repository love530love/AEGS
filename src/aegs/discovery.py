from __future__ import annotations

import re
import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .core import AEGSError, append_event, git_head, governance_dir, project_dir, read_json, write_json


EXCLUDED_DIRECTORIES = {".git", ".aegs", ".venv", "venv", "node_modules", "__pycache__", ".pytest_cache"}
SENSITIVE_NAMES = {".env", "secrets", "credentials", "id_rsa", "id_ed25519"}
SENSITIVE_SUFFIXES = {".pem", ".key", ".p12", ".pfx"}
TEXT_EXTENSIONS = {".py", ".js", ".ts", ".tsx", ".jsx", ".java", ".go", ".rs", ".cs", ".rb", ".php", ".sql", ".sh", ".ps1", ".md", ".yaml", ".yml", ".json", ".toml"}


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _working_tree_dirty(root: Path) -> bool | None:
    result = subprocess.run(["git", "status", "--porcelain"], cwd=root, text=True, capture_output=True, check=False)
    return bool(result.stdout.strip()) if result.returncode == 0 else None


def _relative(root: Path, path: Path) -> str:
    return path.relative_to(root).as_posix()


def _is_sensitive(path: Path) -> bool:
    lowered = path.name.lower()
    return lowered in SENSITIVE_NAMES or lowered.startswith(".env") or path.suffix.lower() in SENSITIVE_SUFFIXES


def _category(relative_path: str) -> str:
    name = Path(relative_path).name.lower()
    parts = {part.lower() for part in Path(relative_path).parts}
    if name in {"package.json", "pyproject.toml", "requirements.txt", "poetry.lock", "pipfile", "go.mod", "cargo.toml"}:
        return "dependency_manifest"
    if ".github" in parts or "ci" in parts or name in {"jenkinsfile", ".gitlab-ci.yml", "azure-pipelines.yml"}:
        return "ci_cd"
    if "test" in parts or name.startswith("test_") or name.endswith("_test.py") or name.endswith(".test.js"):
        return "test"
    if "docs" in parts or Path(relative_path).suffix.lower() == ".md":
        return "documentation"
    if "migration" in parts or "migrations" in parts or Path(relative_path).suffix.lower() == ".sql":
        return "data_contract"
    if name in {"openapi.yaml", "openapi.yml", "openapi.json", "swagger.yaml", "swagger.yml"}:
        return "api_contract"
    if name.endswith((".yml", ".yaml", ".toml", ".ini", ".cfg")) or name in {"dockerfile", "docker-compose.yml", "compose.yml"}:
        return "configuration"
    return "source" if Path(relative_path).suffix.lower() in TEXT_EXTENSIONS else "other"


def _inferred_relations(root: Path, path: Path) -> list[dict[str, Any]]:
    if path.suffix.lower() not in {".py", ".js", ".ts", ".tsx", ".jsx"} or path.stat().st_size > 1_000_000:
        return []
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []
    relations = []
    for number, line in enumerate(lines, start=1):
        target = None
        if path.suffix.lower() == ".py":
            match = re.match(r"\s*(?:from\s+([\w.]+)\s+import|import\s+([\w.]+))", line)
            target = (match.group(1) or match.group(2)) if match else None
        else:
            match = re.search(r"(?:from\s+|require\()['\"]([^'\"]+)", line)
            target = match.group(1) if match else None
        if target:
            relations.append({
                "source": _relative(root, path),
                "target": target,
                "relation": "imports",
                "confidence": "inferred",
                "evidence": f"{_relative(root, path)}:{number}",
            })
    return relations


def discover(root_value: str | Path, max_files: int = 5000) -> dict[str, Any]:
    """Create a read-only, evidence-labelled architecture snapshot."""
    root = project_dir(root_value)
    if not (root / ".aegs" / "charter.json").exists():
        raise AEGSError("Run 'aegs init' before discovering a project")
    files: list[dict[str, Any]] = []
    relationships: list[dict[str, Any]] = []
    excluded_sensitive = 0
    skipped_large = 0
    for path in root.rglob("*"):
        if not path.is_file() or any(part in EXCLUDED_DIRECTORIES for part in path.relative_to(root).parts):
            continue
        if _is_sensitive(path):
            excluded_sensitive += 1
            continue
        if len(files) >= max_files:
            raise AEGSError(f"Discovery stopped at {max_files} files; increase the limit deliberately")
        relative = _relative(root, path)
        size = path.stat().st_size
        category = _category(relative)
        files.append({"path": relative, "size_bytes": size, "category": category})
        if size <= 1_000_000:
            relationships.extend(_inferred_relations(root, path))
        else:
            skipped_large += 1
    category_counts: dict[str, int] = {}
    for item in files:
        category_counts[item["category"]] = category_counts.get(item["category"], 0) + 1
    snapshot_id = f"AS-{uuid.uuid4().hex[:12]}"
    snapshot = {
        "snapshot_id": snapshot_id,
        "schema_version": "0.1",
        "created_at": _now(),
        "root": str(root),
        "git_head": git_head(root),
        "working_tree_dirty": _working_tree_dirty(root),
        "discovery_mode": "read_only",
        "files": files,
        "category_counts": category_counts,
        "relationships": relationships,
        "known_limits": [
            "Relationships are static inferences, not runtime proof.",
            "Sensitive file contents are excluded by filename/suffix policy.",
            "External services and undocumented human knowledge require confirmation.",
        ],
        "excluded_sensitive_file_count": excluded_sensitive,
        "skipped_large_file_count": skipped_large,
        "unresolved_questions": [
            "Which inferred relationships are business-critical?",
            "Which external systems, production constraints, and undocumented dependencies are missing?",
            "Which components may not be changed without explicit owner approval?",
        ],
    }
    aegs = governance_dir(root)
    write_json(aegs / "architecture" / f"{snapshot_id}.json", snapshot)
    write_json(aegs / "current_architecture.json", snapshot)
    state = read_json(aegs / "state.json")
    state["architecture_snapshot"] = snapshot_id
    state["architecture_snapshot_git_head"] = snapshot["git_head"]
    state["unresolved_questions"] = snapshot["unresolved_questions"]
    discovery_fact = f"Read-only architecture snapshot {snapshot_id} created for Git {snapshot['git_head'] or 'non-Git project'}."
    existing_facts = [fact for fact in state.get("verified_facts", []) if not str(fact).startswith("Read-only architecture snapshot ")]
    state["verified_facts"] = [*existing_facts, discovery_fact]
    state["current_goal"] = "Review the architecture snapshot, resolve critical unknowns, and create evidence-backed improvement proposals."
    state["open_risks"] = [
        "Static discovery is not runtime proof; external services and undocumented dependencies require human confirmation.",
        "Sensitive files are intentionally excluded from discovery content.",
    ]
    state["safe_next_actions"] = [
        "Review the current architecture snapshot and confirm or correct unresolved questions.",
        "Create a governed proposal before changing project behavior.",
    ]
    write_json(aegs / "state.json", state)
    append_event(root, "architecture.discovered", {"snapshot_id": snapshot_id, "git_head": snapshot["git_head"], "file_count": len(files)})
    return snapshot
