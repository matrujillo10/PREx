"""Manifest reader for `.review/types.yaml`.

v0.1: a flat list of generic checklist items applied to every PR. The schema
is forward-compatible with type-keyed sections (feat/fix/chore/...) for v0.2.
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional

import yaml
from pydantic import BaseModel, ConfigDict, Field

from prex.schemas.brief import PRType


class ManifestRule(BaseModel):
    """One predicate-driven checklist item declared in the manifest."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(description="Stable id (e.g. 'public_symbol_modified_without_test').")
    text: str = Field(description="Human-readable item rendered in the UI.")
    predicate: str = Field(description="Name of a function in `prex.manifest.predicates`.")
    required: bool = Field(default=False, description="Whether reviewer must satisfy this item.")
    applies_when: Optional[str] = Field(
        default=None,
        description="Optional predicate function gating whether this rule applies. None = always.",
    )


class ManifestSection(BaseModel):
    """A grouping of rules. v0.1 ships one generic section."""

    model_config = ConfigDict(extra="forbid")

    type: Optional[PRType] = Field(
        default=None, description="When set, this section applies only to PRs of this type."
    )
    rules: List[ManifestRule] = Field(default_factory=list)


class Manifest(BaseModel):
    """Top-level manifest. Parsed from `.review/types.yaml`."""

    model_config = ConfigDict(extra="forbid")

    schema_version: str = Field(default="0.1.0")
    sections: List[ManifestSection] = Field(default_factory=list)


_DEFAULT_MANIFEST_PATH = Path(__file__).parent.parent.parent / "examples" / ".review" / "types.yaml"


def find_manifest(repo_path: Path, override: Optional[Path] = None) -> Optional[Path]:
    """Locate manifest. Order: explicit override > target repo `.review/types.yaml` > bundled default."""
    if override and override.exists():
        return override
    candidate = repo_path / ".review" / "types.yaml"
    if candidate.exists():
        return candidate
    if _DEFAULT_MANIFEST_PATH.exists():
        return _DEFAULT_MANIFEST_PATH
    return None


def load_manifest(path: Path) -> Manifest:
    """Parse a manifest YAML file into a `Manifest` model."""
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return Manifest.model_validate(raw)


__all__ = ["Manifest", "ManifestRule", "ManifestSection", "find_manifest", "load_manifest"]
