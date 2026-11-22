# Scientific data and static packaging

Use this reference for numerical results, 3D assets, data-rich sites and single-file export. The two inputs that inspired this skill are `00_SRF.md` (a guided 3D soil–structure interaction explorer) and `01_Inversion.md` (an interactive finite-fault inversion presentation). Their common architecture is generalized here. Source-specific datasets, names and conventions are examples only.

## Data contract

Keep raw inputs read-only, versioned or identified by checksum. An inventory entry should contain asset ID, source path/URL/DOI, source date/version, permission or redistribution license, physical quantity, units, coordinates/time conventions, shape/dtype, preparation script and display transformations. Mark unavailable optional fields explicitly. Use stable entity IDs and verify relations (e.g. node IDs referenced by elements, sensor IDs referenced by traces). Do not expose internal paths or sensitive metadata in the public manifest; keep a separate private build inventory if necessary.

A modest JSON asset could use this shape (illustrative only):

```json
{
  "schema_version": 1,
  "id": "case-a",
  "title": "Case A",
  "kind": "simulation",
  "source_id": "source-a",
  "time": {"unit": "s", "t0": 0, "dt": 0.01},
  "series": [{"id": "sensor-a-x", "quantity": "acceleration", "unit": "m/s^2", "values": []}],
  "summary": {},
  "limitations": []
}
```

Empty example arrays are not valid evidence: validate populated assets against the real contract. Use explicit timestamps for irregular sampling. Use `null` for missing JSON data; handle non-finite values before serialization. Avoid rounding until after computing summary statistics. Ensure the UI cannot misinterpret empty datasets as zero.

## Storage strategies

| Asset | Recommended storage | Validation |
|---|---|---|
| Small case metadata, parameters, metrics | JSON | schema, IDs, ranges, units |
| Regular grids, mesh geometry, long traces | binary typed arrays plus JSON manifest | byte offsets, endian, lengths, index bounds |
| Maps and images | WebP/PNG/SVG as appropriate | extent, credit, orientation, transparency |
| Many similar cases | case-specific assets, lazy-load if folder build | identical schema, selection consistency |
| Transient large mesh fields | time blocks, decimation or SVD/POD if justified | reconstruction error on representative locations and critical responses |

For a binary layout prefer C-contiguous, little-endian arrays, offsets aligned to at least the largest dtype alignment used (4 bytes for up to 32-bit types). Include `key`, `dtype`, `shape`, `offset`, optional `scale` and `add`, and units. Validate nonnegative offsets and lengths, alignment, type whitelist, bounds within the blob, and no accidental overlap. On a non-little-endian JS runtime decode explicitly with `DataView`. Convert to physical values with `raw * scale + add`; handle masks before decoding or plotting. Use float32 only if error is acceptable; retain double precision when needed.

```json
{"key":"elevation","dtype":"uint16","shape":[100,100],"offset":0,"scale":0.1,"add":-50,"unit":"m"}
```

This example is a schema illustration, not a dataset. The resulting quantization step is 0.1 m; verify clipping and reconstruction errors from the actual exported values.

## Reduction and numerical integrity

- For geometry, use an explicit visualization LOD and retain entity IDs so inspector values originate from the real model. Preserve boundaries and important geometric features.
- For time histories, use anti-aliasing for uniform resampling; consider min/max envelope rendering to preserve peaks in long records. Keep original peak metrics, event times, spectra and integrations computed from the full-resolution source. Compare observation and simulation on a common timebase, units and processing convention; do not imply agreement using mismatched scales.
- For quantization, document step, range, clipping count and achieved errors. For compressed fields, test reconstructed peaks, signs, localized extreme values and quantities relevant to the scientific conclusion. A global RMS error alone may hide local failures.
- For low-rank displacement histories, e.g. `D ~= U_r diag(s_r) V_r^T`, keep spatial and temporal bases and reconstruct only the displayed time index. Choose rank based on measured error, not a fixed number of modes. Interpolate in time only where justified; label approximations and deformation exaggeration.
- Set domain-specific tolerances in SPEC before checking results; example tolerances from one study do not generalize automatically to another.

## Coordinates and time

Choose the model frame before building UI. For geographic applications, record CRS/EPSG, datum, local origin and projection/reprojection method. Document vertical datum and elevation versus depth. For mechanical models, document axes, orientation, units and origin; convert millimeters to meters once where appropriate. A render frame with y up may map canonical east/north/up to `(east, up, -north)`; verify handedness and test a known point and positive rotation. Do not impose this mapping on incompatible model frames. Label vertical exaggeration separately from deformation scaling. Store time in physical units; distinguish absolute, event-relative, stage-relative and normalized axes. Display time playback speed is not physical model time.

## Two publication modes

### Single-file (default)

Development may use a local HTTP server and external files; `build.py` assembles an equivalent published `dist/index.html`. Embed CSS, executable app JS, images and prepared data. One strategy is a non-executable JSON script element containing a manifest and base64 blobs; read its `textContent` using `JSON.parse`. For large blobs gzip before base64; base64 expands compressed bytes by about one-third. Already compressed images generally do not benefit from gzip. Browser decompression can use `DecompressionStream('gzip')` where supported, with a tested fallback or an explicit compatibility requirement.

Illustrative safe JSON embedding in Python:

```python
import base64, gzip, json

def pack_asset(raw: bytes, compress: bool = True):
    payload = gzip.compress(raw, mtime=0) if compress else raw
    return {"gzip": compress, "base64": base64.b64encode(payload).decode("ascii")}

def json_script_text(obj):
    # Prevent any embedded HTML end tag from terminating the script element.
    return json.dumps(obj, ensure_ascii=True, allow_nan=False, separators=(",", ":")).replace("<", "\\u003c")
```

Example HTML template marker: `<script id="embedded-data" type="application/json">@@DATA@@</script>`. Replace exactly once. For app JS and CSS use a proper build/inline strategy that preserves syntax, relative URLs and import resolution; do not blindly substitute inside arbitrary source text. Validate that no unresolved markers remain. Use local assets via data URLs where appropriate. If bundling multiple ES modules, resolve imports/exports using a suitable bundler rather than naive concatenation. No local fetch or local module imports may remain in a double-click artifact.

Pinned CDN dependencies (e.g. an ES module or font) mean network access is required: disclose it. A fully offline build must bundle or inline all dependencies, and must run with internet access disabled. Vendor libraries with their licenses; do not claim browser cache guarantees offline access. Keep a file-origin test separate from the offline test.

### Static folder (large or frequently updated data)

Use `dist/index.html`, relative local JS/CSS, and `dist/assets/`. Lazy-load data on chapter/case selection, report loading or errors, cancel/ignore stale requests, and use versioned filenames or coherent caching when applicable. Same-origin relative URLs must work below arbitrary paths, not just `/`. A file using local `fetch` normally needs HTTP; provide `python -m http.server 8765 --directory dist` and the corresponding local URL. Do not require a compute backend. Prefer this mode to an overwhelming single HTML when scientific accuracy or mobile startup would otherwise suffer.

## Preparation/build reports

For each script include input identifiers, output schema, sizes, counts, ranges, checks, tolerances and warnings. Fail if required data is not present or invalid rather than generating a deceptive page. Optional data can be omitted with a reader-visible reason. For a large campaign record generated manifest + validation report in reproducible form (JSON and/or Markdown). Verify repeated builds with identical sources produce equivalent contents; when embedding gzip use deterministic timestamps if possible. Prefer a documented command that runs the preparation steps in dependency order, followed by packaging and tests.
