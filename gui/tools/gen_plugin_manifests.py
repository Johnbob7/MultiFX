"""Generate plugin manifest files from metadata.

This script walks plugin configuration directories, reads per-plugin metadata,
normalizes it into a manifest format, and writes individual JSON manifest files
into the manifests directory.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, Iterable, List

DEFAULT_METADATA_FILENAME = "metadata.json"


def _load_metadata(plugin_dir: Path, metadata_filename: str) -> Dict:
    metadata_file = plugin_dir / metadata_filename
    if metadata_file.is_file():
        try:
            with metadata_file.open("r", encoding="utf-8") as handle:
                data = json.load(handle)
                if isinstance(data, dict):
                    return data
                print(f"Ignoring metadata in {metadata_file} (expected object)")
        except Exception as exc:  # noqa: BLE001 - surface parsing errors
            print(f"Failed to parse metadata for {plugin_dir.name}: {exc}")
    slug = plugin_dir.name
    return {
        "name": slug.replace("_", " "),
        "uri": f"urn:multifx:{slug.lower()}",
        "channels": "mono",
        "inputs": ["in"],
        "outputs": ["out"],
        "parameters": [],
    }


def _normalize_parameters(parameter_data: Iterable[dict]) -> List[dict]:
    normalized: List[dict] = []
    for param in parameter_data or []:
        if not isinstance(param, dict):
            continue
        symbol = param.get("symbol")
        if not symbol:
            print("Skipping parameter without symbol in metadata")
            continue
        normalized.append(
            {
                "type": param.get("type", "lv2"),
                "name": param.get("name", symbol),
                "symbol": symbol,
                "mode": param.get("mode", "dial"),
                "min": param.get("min", 0),
                "max": param.get("max", 1),
                "default": param.get("default", param.get("value", 0)),
            }
        )
    return normalized


def _extract_io(metadata: Dict) -> tuple[list, list]:
    inputs = metadata.get("inputs")
    outputs = metadata.get("outputs")
    if inputs is None or outputs is None:
        io_data = metadata.get("io", {})
        if inputs is None:
            inputs = io_data.get("inputs", ["in"])
        if outputs is None:
            outputs = io_data.get("outputs", ["out"])
    return list(inputs or ["in"]), list(outputs or ["out"])


def _normalize_plugin_metadata(plugin_dir: Path, metadata: Dict) -> Dict:
    inputs, outputs = _extract_io(metadata)
    slug = plugin_dir.name
    return {
        "name": metadata.get("name", slug.replace("_", " ")),
        "uri": metadata.get("uri", f"urn:multifx:{slug.lower()}"),
        "channels": metadata.get("channels", "mono"),
        "inputs": inputs,
        "outputs": outputs,
        "bypass": metadata.get("bypass", 0),
        "parameters": _normalize_parameters(metadata.get("parameters", [])),
    }


def _iter_plugin_dirs(plugin_root: Path) -> Iterable[Path]:
    for child in sorted(plugin_root.iterdir()):
        if child.name == "manifests" or not child.is_dir():
            continue
        yield child


def generate_manifests(plugin_root: Path, manifest_dir: Path, metadata_filename: str = DEFAULT_METADATA_FILENAME) -> List[Path]:
    manifest_dir.mkdir(parents=True, exist_ok=True)
    written: List[Path] = []
    for plugin_dir in _iter_plugin_dirs(plugin_root):
        metadata = _load_metadata(plugin_dir, metadata_filename)
        plugin_entry = _normalize_plugin_metadata(plugin_dir, metadata)
        manifest_path = manifest_dir / f"{plugin_dir.name}.json"
        manifest_payload = {"plugins": [plugin_entry]}
        with manifest_path.open("w", encoding="utf-8") as handle:
            json.dump(manifest_payload, handle, indent=2)
            handle.write("\n")
        written.append(manifest_path)
    return written


def main():
    parser = argparse.ArgumentParser(description="Generate plugin manifest files")
    parser.add_argument(
        "--plugin-root",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "config" / "plugins",
        help="Root folder that contains plugin directories",
    )
    parser.add_argument(
        "--manifest-dir",
        type=Path,
        default=None,
        help="Destination directory for generated manifests (defaults to <plugin-root>/manifests)",
    )
    parser.add_argument(
        "--metadata-filename",
        type=str,
        default=DEFAULT_METADATA_FILENAME,
        help="Metadata filename to look for inside each plugin directory",
    )
    args = parser.parse_args()

    manifest_dir = args.manifest_dir or args.plugin_root / "manifests"
    manifest_paths = generate_manifests(args.plugin_root, manifest_dir, args.metadata_filename)
    print(f"Wrote {len(manifest_paths)} manifest(s) to {manifest_dir}")


if __name__ == "__main__":
    main()
