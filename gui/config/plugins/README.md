# Plugin metadata and manifests

This directory contains source material for each plugin and the manifests that
power the GUI's plugin catalog. A small generator script converts per-plugin
metadata into normalized manifest files that the GUI loads at startup.

## Metadata files

Each plugin directory may include a `metadata.json` file. The generator falls
back to sensible defaults (name derived from folder, mono IO, empty parameter
list) when the file is missing, but providing metadata keeps manifests accurate
and consistent.

### Supported fields

```jsonc
{
  "name": "Readable plugin name",          // Defaults to directory name
  "uri": "urn:multifx:my_plugin",         // Required by mod-host/LV2
  "channels": "mono",                     // "mono" or "stereo"
  "inputs": ["in"],                        // Input port labels
  "outputs": ["out"],                      // Output port labels
  "parameters": [
    {
      "symbol": "gain",                   // Required
      "name": "Gain",                     // Defaults to symbol
      "type": "lv2",                      // Defaults to "lv2"
      "mode": "dial",                     // "dial", "button", or "selector"
      "min": 0,                            // Required when parameters are present
      "max": 1,                            // Required when parameters are present
      "default": 0.5                       // Optional, defaults to 0
    }
  ],
  "bypass": 0                              // Optional bypass value
}
```

An alternative structure groups IO under `io`, which is helpful when the same
metadata feeds other tools:

```json
{"io": {"inputs": ["inL", "inR"], "outputs": ["outL", "outR"]}}
```

The generator merges either representation, preferring `inputs`/`outputs` when
both are present.

## Generating manifests

Run the generator to refresh manifests in `gui/config/plugins/manifests/`:

```bash
python gui/tools/gen_plugin_manifests.py
```

You can optionally ask the generator to auto-populate `parameters` for plugins
whose `metadata.json` omits them by querying installed LV2 metadata via
[`python-lilv`](https://drobilla.net/software/lilv):

```bash
python gui/tools/gen_plugin_manifests.py --discover-parameters
```

Discovery is best-effort: if `python-lilv` is not available or the requested
plugin URI cannot be resolved, the generator logs a warning and leaves the
parameters empty.

The script walks every plugin subdirectory (skipping `manifests/`), normalizes
metadata, and writes one manifest per plugin. Each manifest is a JSON file with
this shape:

```json
{"plugins": [{"name": "My Plugin", "uri": "urn:multifx:my_plugin", ...}]}
```

## Startup/build hook

The GUI calls `ensure_plugin_manifests` during startup to regenerate manifests
when they are missing or when a plugin's `metadata.json` file is newer than the
existing manifest. Include the generator in your build process (for example,
`python gui/tools/gen_plugin_manifests.py`) to ensure production images ship
with up-to-date manifests.
