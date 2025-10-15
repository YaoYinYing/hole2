"""Integration tests that exercise the documented example inputs."""
from __future__ import annotations

import re
import subprocess
import os
import shutil
from pathlib import Path
from typing import Dict, Optional

import pytest


ROOT = Path(__file__).resolve().parents[1]
HOLE_EXE = ROOT / "exe" / "hole"
RADII_FILE = ROOT / "rad" / "simple.rad"
LEGACY_ROOT = Path.home() / "hole2"


def _ensure_legacy_layout() -> None:
    """Ensure legacy hard-coded paths resolve for the HOLE binary."""

    legacy_rad = LEGACY_ROOT / "rad"
    if legacy_rad.exists():
        return

    LEGACY_ROOT.mkdir(parents=True, exist_ok=True)

    # Attempt to mirror the repository under ~/hole2 so the binary can
    # resolve its historical lookups into ~/hole2/rad/*. The macOS CI
    # runners are case-sensitive enough that a simple symlink suffices and
    # avoids duplicating the checkout, but fall back to a copy if symlinks
    # are unavailable.
    try:
        if LEGACY_ROOT.is_dir() and not LEGACY_ROOT.is_symlink():
            # The directory was just created above and is empty; replace it
            # with a symlink that mirrors the repository checkout.
            LEGACY_ROOT.rmdir()
        os.symlink(ROOT, LEGACY_ROOT, target_is_directory=True)
    except (OSError, NotImplementedError):
        if not LEGACY_ROOT.exists():
            shutil.copytree(ROOT, LEGACY_ROOT)


def _require_binary() -> Path:
    """Ensure the HOLE binary exists before running the tests."""

    _ensure_legacy_layout()

    if not HOLE_EXE.exists():  # pragma: no cover - defensive guard
        pytest.fail(
            "The HOLE binary is missing. Build it first with `make -C src`."
        )
    return HOLE_EXE


def _extract_card_value(text: str, card: str) -> Optional[str]:
    pattern = re.compile(
        r"^({}\s+)(\S+)".format(re.escape(card)),
        re.IGNORECASE | re.MULTILINE,
    )
    match = pattern.search(text)
    if not match:
        return None
    return match.group(2)


def _set_card_value(text: str, card: str, value: Path | str) -> str:
    pattern = re.compile(
        r"^({}\s+)(\S+)(.*)$".format(re.escape(card)),
        re.IGNORECASE | re.MULTILINE,
    )

    def repl(match: re.Match[str]) -> str:
        return f"{match.group(1)}{value}{match.group(3)}"

    updated, count = pattern.subn(repl, text, count=1)
    return updated if count else text


def _run_example(
    example: str, input_name: str, tmp_path: Path, seed: Optional[int] = None
) -> str:
    exe = _require_binary()
    example_dir = ROOT / "examples" / example
    input_text = (example_dir / input_name).read_text()

    coord_value = _extract_card_value(input_text, "coord")
    if coord_value:
        coord_path = Path(coord_value)
        if not coord_path.is_absolute():
            coord_path = example_dir / coord_path
        input_text = _set_card_value(input_text, "coord", coord_path.resolve())

    input_text = _set_card_value(input_text, "radius", RADII_FILE.resolve())

    if _extract_card_value(input_text, "sphpdb"):
        sphere_file = (tmp_path / f"{example}.sph").resolve()
        input_text = _set_card_value(input_text, "sphpdb", sphere_file)

    if seed is not None and not re.search(r"(?im)^raseed\s", input_text):
        if not input_text.endswith("\n"):
            input_text += "\n"
        input_text += f"raseed {seed}\n"

    result = subprocess.run(
        [str(exe)],
        input=input_text,
        text=True,
        capture_output=True,
        cwd=tmp_path,
        check=True,
    )

    return result.stdout


MIN_RADIUS_PATTERN = re.compile(
    r"Minimum radius found[^0-9]*([0-9.]+)", re.IGNORECASE | re.MULTILINE
)


TAG_PATTERN = re.compile(
    r"\(TAG\s+\d+\s+Rmin=\s+([0-9.]+)\s+Gmacro=\s+([0-9.]+)(?:\s+Conn_Gmacro=\s+([0-9.\-]+))?",
    re.MULTILINE,
)


EXAMPLE_CASES: Dict[str, Dict[str, float]] = {
    "01_gramicidin_1grm": {
        "input": "hole.inp",
        "min_radius": 1.198,
        "tag_rmin": 1.19772,
        "gmacro": 274.61378,
        "conn_gmacro": -1.0,
        "seed": 6140831,
    },
    "02_choleratoxin_1chb": {
        "input": "02_hole.inp",
        "min_radius": 3.035,
        "tag_rmin": 3.03465,
        "gmacro": 2113.82987,
        "conn_gmacro": 5028.25463,
        "seed": 15072553,
    },
    "03_maltoporin_1af6": {
        "input": "03_example.inp",
        "min_radius": 2.049,
        "tag_rmin": 2.04894,
        "gmacro": 1221.09109,
        "conn_gmacro": -1.0,
        "seed": 15072611,
    },
}


@pytest.mark.parametrize("example", sorted(EXAMPLE_CASES))
def test_examples_follow_documented_outputs(example: str, tmp_path: Path) -> None:
    case = EXAMPLE_CASES[example]
    stdout = _run_example(example, case["input"], tmp_path, seed=case.get("seed"))

    assert "HOLE: normal completion" in stdout

    min_radius_match = MIN_RADIUS_PATTERN.search(stdout)
    assert min_radius_match, "Minimum radius not reported"
    min_radius = float(min_radius_match.group(1))
    assert min_radius == pytest.approx(case["min_radius"], abs=1e-3)

    tag_match = TAG_PATTERN.search(stdout)
    assert tag_match, "TAG summary line missing"

    tag_rmin = float(tag_match.group(1))
    gmacro = float(tag_match.group(2))
    assert tag_rmin == pytest.approx(case["tag_rmin"], abs=1e-5)
    assert gmacro == pytest.approx(case["gmacro"], rel=1e-6, abs=1e-3)

    conn_expected = case.get("conn_gmacro")
    if conn_expected is not None and tag_match.group(3) is not None:
        conn_value = float(tag_match.group(3))
        assert conn_value == pytest.approx(conn_expected, abs=1e-2)
