#!/usr/bin/env python3
"""Scan JUCE plugin source files for addParameter declarations.

Usage:
    python scripts/find_parameters.py [PATH ...]

If a PATH is a directory, all ``.h`` files under it are scanned recursively.
By default, the script searches ``gui/config/plugins``.

Set ``--format json`` to emit JSON instead of a table.
"""
from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Iterable, List

# Matches patterns like:
#   addParameter (gain = new juce::AudioParameterFloat({"gain", 1}, "Gain", 0.0f, 3.0f, 1.0f));
PARAM_PATTERN = re.compile(
    r"addParameter\s*\(\s*(?P<var>\w+)\s*=\s*new\s+(?:juce::)?"
    r"(?P<type>AudioParameter\w+)\s*\(\s*\{\s*\"(?P<id>[^\"]+)\"[^}]*\}\s*,\s*"
    r"\"(?P<label>[^\"]+)\"\s*,\s*(?P<min>[^,]+)\s*,\s*(?P<max>[^,]+)\s*,\s*(?P<default>[^,)]+)\)",
    re.MULTILINE,
)


@dataclass
class ParameterMatch:
    file: Path
    line: int
    var: str
    type: str
    param_id: str
    label: str
    min: str
    max: str
    default: str


def iter_files(paths: Iterable[Path]) -> Iterable[Path]:
    for path in paths:
        if path.is_dir():
            yield from path.rglob("*.h")
        elif path.suffix == ".h":
            yield path


def find_parameters(file_path: Path) -> List[ParameterMatch]:
    text = file_path.read_text(encoding="utf-8", errors="ignore")
    matches: List[ParameterMatch] = []
    for match in PARAM_PATTERN.finditer(text):
        start = match.start()
        line = text.count("\n", 0, start) + 1
        matches.append(
            ParameterMatch(
                file=file_path,
                line=line,
                var=match.group("var"),
                type=match.group("type"),
                param_id=match.group("id"),
                label=match.group("label"),
                min=match.group("min").strip(),
                max=match.group("max").strip(),
                default=match.group("default").strip(),
            )
        )
    return matches


def render_table(results: List[ParameterMatch]) -> None:
    if not results:
        print("No parameters found.")
        return

    headers = ["File", "Line", "Var", "Type", "ID", "Label", "Min", "Max", "Default"]
    rows = [
        [
            str(r.file),
            str(r.line),
            r.var,
            r.type,
            r.param_id,
            r.label,
            r.min,
            r.max,
            r.default,
        ]
        for r in results
    ]

    widths = [max(len(row[i]) for row in [headers] + rows) for i in range(len(headers))]

    def fmt(row: list[str]) -> str:
        return "  ".join(cell.ljust(widths[i]) for i, cell in enumerate(row))

    print(fmt(headers))
    print("  ".join("-" * w for w in widths))
    for row in rows:
        print(fmt(row))


def main() -> None:
    parser = argparse.ArgumentParser(description="Find JUCE addParameter declarations.")
    parser.add_argument("paths", nargs="*", type=Path, default=[Path("gui/config/plugins")])
    parser.add_argument("--format", choices=["table", "json"], default="table")
    args = parser.parse_args()

    files = list(iter_files(args.paths))
    results: List[ParameterMatch] = []
    for file_path in files:
        results.extend(find_parameters(file_path))

    # Sort for stable output
    results.sort(key=lambda r: (str(r.file), r.line))

    if args.format == "json":
        serializable = []
        for r in results:
            data = asdict(r)
            data["file"] = str(r.file)
            serializable.append(data)

        print(json.dumps(serializable, indent=2))
    else:
        render_table(results)


if __name__ == "__main__":
    main()
