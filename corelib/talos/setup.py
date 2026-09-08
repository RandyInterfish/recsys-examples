# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Wheel-build hook: download the bundled veloq binary + skill tarball.

Project metadata still lives in pyproject.toml. This file only adds a
custom `build_py` (and `bdist_wheel`) that, before setuptools sweeps
package contents into the wheel, fetches:

  1. veloq native binary  → skills/bin/veloq
  2. veloq-skills.tar.gz  → skills/nsys_profile_analysis/{SKILL.md, references/}
                              and skills/ncu_profile_analysis/{SKILL.md, references/}

Both come from veloq's public GitHub Releases (github.com/lucifer1004/veloq)
— same source veloq's own install.sh uses, so the binary and the skills are
guaranteed to match.

Configuration (from pyproject.toml's [tool.talos]):
  veloq-version    GitHub release tag to pin (required).
  veloq-base-url   Optional release-download base URL override.

Target-platform selection:
  VELOQ_PLATFORM env var picks one of {x86_64-linux, aarch64-linux,
  x86_64-macos, aarch64-macos}. Default = current build host.
"""

from __future__ import annotations

import os
import platform
import shutil
import sys
import tarfile
import tempfile
import urllib.request
from pathlib import Path

try:
    import tomllib  # py311+
except ModuleNotFoundError:
    import tomli as tomllib  # build-only dep, declared in [build-system].requires

from setuptools import setup
from setuptools.command.build_py import build_py

from wheel.bdist_wheel import bdist_wheel


HERE = Path(__file__).resolve().parent
SKILLS_ROOT = HERE / "skills"
BIN_DIR = SKILLS_ROOT / "bin"
BIN_DEST = BIN_DIR / "veloq"

DEFAULT_BASE_URL = "https://github.com/lucifer1004/veloq/releases/download"

# (target key → veloq asset filename, wheel platform tag)
PLATFORMS = {
    "x86_64-linux":  ("veloq-x86_64-linux",  "manylinux2014_x86_64"),
    "aarch64-linux": ("veloq-aarch64-linux", "manylinux2014_aarch64"),
    "x86_64-macos":  ("veloq-x86_64-macos",  "macosx_11_0_x86_64"),
    "aarch64-macos": ("veloq-aarch64-macos", "macosx_11_0_arm64"),
}


# ─────────────────────────────────────────────────────────────────────────────
# Config + platform resolution
# ─────────────────────────────────────────────────────────────────────────────

def _read_config() -> dict:
    with open(HERE / "pyproject.toml", "rb") as f:
        cfg = tomllib.load(f)
    section = cfg.get("tool", {}).get("talos", {})
    if "veloq-version" not in section:
        raise SystemExit(
            "pyproject.toml is missing [tool.talos].veloq-version — "
            "pin a release tag (e.g. \"v0.2.1\") so the build can fetch a "
            "matching binary and skill tarball."
        )
    return section


def _detect_host_platform() -> str:
    sysname = sys.platform
    mach = platform.machine().lower()
    if sysname.startswith("linux"):
        if mach == "x86_64":
            return "x86_64-linux"
        if mach in ("aarch64", "arm64"):
            return "aarch64-linux"
    elif sysname == "darwin":
        if mach == "x86_64":
            return "x86_64-macos"
        if mach in ("aarch64", "arm64"):
            return "aarch64-macos"
    raise SystemExit(
        f"unsupported build host {sysname}/{mach}; set VELOQ_PLATFORM explicitly "
        f"to one of {sorted(PLATFORMS)}"
    )


def _resolve_platform() -> str:
    env = os.environ.get("VELOQ_PLATFORM")
    if env:
        if env not in PLATFORMS:
            raise SystemExit(
                f"VELOQ_PLATFORM={env!r} unrecognized; choose from {sorted(PLATFORMS)}"
            )
        return env
    return _detect_host_platform()


# ─────────────────────────────────────────────────────────────────────────────
# Fetch helpers
# ─────────────────────────────────────────────────────────────────────────────

def _download(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    sys.stderr.write(f"[veloq-build] GET {url}\n")
    with urllib.request.urlopen(url) as resp, open(dest, "wb") as out:
        shutil.copyfileobj(resp, out)


def _fetch_binary(base_url: str, version: str, asset: str) -> None:
    url = f"{base_url}/{version}/{asset}"
    _download(url, BIN_DEST)
    BIN_DEST.chmod(0o755)


def _fetch_skills(base_url: str, version: str) -> None:
    """Pull veloq-skills.tar.gz and explode it under skills/<pkg_name>/.

    The tarball entries look like:
        .claude/skills/<skill-slug>/SKILL.md
        .claude/skills/<skill-slug>/references/*.md

    We strip the leading `.claude/skills/` prefix and remap the skill slug
    to its Python-package form (`-` → `_`) so it slots into the talos
    namespace as a real subpackage. SKILL.md / references/ get written
    *inside* the existing `__init__.py`-bearing source-tree directory.
    """
    url = f"{base_url}/{version}/veloq-skills.tar.gz"
    with tempfile.NamedTemporaryFile(suffix=".tar.gz", delete=False) as tmp:
        tmp_path = Path(tmp.name)
    try:
        _download(url, tmp_path)
        with tarfile.open(tmp_path, "r:gz") as tar:
            for member in tar.getmembers():
                parts = Path(member.name).parts
                if len(parts) < 3 or parts[0] != ".claude" or parts[1] != "skills":
                    continue
                slug = parts[2]              # e.g. "nsys-profile-analysis"
                pkg = slug.replace("-", "_")  # e.g. "nsys_profile_analysis"
                rel = Path(*parts[3:]) if len(parts) > 3 else None
                if rel is None or str(rel) in (".", ""):
                    continue
                target = SKILLS_ROOT / pkg / rel
                if member.isdir():
                    target.mkdir(parents=True, exist_ok=True)
                    continue
                if not member.isfile():
                    continue
                target.parent.mkdir(parents=True, exist_ok=True)
                src = tar.extractfile(member)
                if src is None:
                    continue
                with open(target, "wb") as out:
                    shutil.copyfileobj(src, out)
    finally:
        tmp_path.unlink(missing_ok=True)


# ─────────────────────────────────────────────────────────────────────────────
# Custom commands
# ─────────────────────────────────────────────────────────────────────────────

class BuildWithVeloq(build_py):
    """Fetch veloq artifacts before the standard build_py pass."""

    def run(self):
        cfg = _read_config()
        version = cfg["veloq-version"]
        base_url = cfg.get("veloq-base-url", DEFAULT_BASE_URL)
        plat_key = _resolve_platform()
        asset = PLATFORMS[plat_key][0]

        sys.stderr.write(
            f"[veloq-build] platform={plat_key}  version={version}  asset={asset}\n"
        )
        _fetch_binary(base_url, version, asset)
        _fetch_skills(base_url, version)
        super().run()


class BdistWheelTagged(bdist_wheel):
    """Mark the wheel as platform-specific and pin the platform tag."""

    def finalize_options(self):
        super().finalize_options()
        self.root_is_pure = False  # not a pure-Python wheel

    def get_tag(self):
        wheel_tag = PLATFORMS[_resolve_platform()][1]
        return "py3", "none", wheel_tag


# ─────────────────────────────────────────────────────────────────────────────
# Entry
# ─────────────────────────────────────────────────────────────────────────────

setup(cmdclass={"build_py": BuildWithVeloq, "bdist_wheel": BdistWheelTagged})
