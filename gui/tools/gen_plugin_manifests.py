"""Generate plugin manifest files from metadata.

This script walks plugin configuration directories, reads per-plugin metadata,
normalizes it into a manifest format, and writes individual JSON manifest files
into the manifests directory.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Callable, Dict, Iterable, List, Optional

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


def _node_to_number(node: object) -> Optional[float]:
    """Best-effort conversion for lilv nodes to floats."""

    if node is None:
        return None
    for attr in ("as_float", "as_double", "as_int"):
        converter = getattr(node, attr, None)
        if converter is None:
            continue
        try:
            return float(converter())
        except Exception:
            continue
    try:
        return float(node)
    except Exception:
        return None


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


def _normalize_plugin_metadata(
    plugin_dir: Path,
    metadata: Dict,
    discover_params: Optional[Callable[[str], List[dict]]] = None,
) -> Dict:
    inputs, outputs = _extract_io(metadata)
    slug = plugin_dir.name
    parameters = _normalize_parameters(metadata.get("parameters", []))
    if not parameters and discover_params:
        uri = metadata.get("uri", f"urn:multifx:{slug.lower()}")
        try:
            parameters = discover_params(uri)
        except Exception as exc:  # noqa: BLE001 - discovery is best-effort
            print(f"Failed to discover parameters for {uri}: {exc}")
    return {
        "name": metadata.get("name", slug.replace("_", " ")),
        "uri": metadata.get("uri", f"urn:multifx:{slug.lower()}"),
        "channels": metadata.get("channels", "mono"),
        "inputs": inputs,
        "outputs": outputs,
        "bypass": metadata.get("bypass", 0),
        "parameters": parameters,
    }


def _iter_plugin_dirs(plugin_root: Path) -> Iterable[Path]:
    for child in sorted(plugin_root.iterdir()):
        if child.name == "manifests" or not child.is_dir():
            continue
        yield child


def _maybe_make_lilv_discovery(enabled: bool) -> Optional[Callable[[str], List[dict]]]:
    if not enabled:
        return None
    try:
        import lilv  # type: ignore
    except Exception as exc:  # noqa: BLE001 - optional dependency
        print(f"Parameter discovery requested but lilv is unavailable: {exc}")
        return None

    world = lilv.World()
    world.load_all()
    lv2 = world.ns.lv2

    def discover(uri: str) -> List[dict]:
        plugin = next((p for p in world.get_all_plugins() if str(p.get_uri()) == uri), None)
        if plugin is None:
            print(f"Could not find LV2 plugin with URI {uri} for parameter discovery")
            return []
        params: List[dict] = []
        for port in plugin.get_ports():
            if not port.is_a(lv2.ControlPort):
                continue
            symbol = port.get_symbol()
            if not symbol:
                continue
            name = port.get_name() or symbol
            default, minimum, maximum = port.get_range()
            mode = "button" if port.has_property(lv2.toggled) else "dial"
            params.append(
                {
                    "type": "lv2",
                    "name": name,
                    "symbol": symbol,
                    "mode": mode,
                    "min": _node_to_number(minimum) or 0,
                    "max": _node_to_number(maximum) or 1,
                    "default": _node_to_number(default) or 0,
                }
            )
        return params

    return discover


def generate_manifests(
    plugin_root: Path,
    manifest_dir: Path,
    metadata_filename: str = DEFAULT_METADATA_FILENAME,
    discover_parameters: bool = False,
) -> List[Path]:
    manifest_dir.mkdir(parents=True, exist_ok=True)
    written: List[Path] = []
    discover = _maybe_make_lilv_discovery(discover_parameters)
    for plugin_dir in _iter_plugin_dirs(plugin_root):
        metadata = _load_metadata(plugin_dir, metadata_filename)
        plugin_entry = _normalize_plugin_metadata(plugin_dir, metadata, discover)
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
    parser.add_argument(
        "--discover-parameters",
        action="store_true",
        help="Attempt to auto-populate parameters using installed LV2 metadata when metadata.json omits them",
    )
    args = parser.parse_args()

    manifest_dir = args.manifest_dir or args.plugin_root / "manifests"
    manifest_paths = generate_manifests(
        args.plugin_root,
        manifest_dir,
        args.metadata_filename,
        discover_parameters=args.discover_parameters,
    )
    print(f"Wrote {len(manifest_paths)} manifest(s) to {manifest_dir}")


if __name__ == "__main__":
    main()
