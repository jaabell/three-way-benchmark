# The I-beam benchmark

An [interactive research explorer](SPEC.md) for the Esmeralda beam study. The two surfaces, scalar fields, rank ownership, charts, and inspection controls share a gravity step. Presentation view hides the surrounding sections for video capture. Its camera presets and keyboard arrows work without a mouse.

[Open the unlisted explorer](https://joseabell.com/apps/beam-benchmark-e25983d5a2ab5975/)

## Build and preview

The data preparation uses Esmeralda’s ParaView Python 6.2.1 and NumPy. It reads the seven archived VTK series and the benchmark CSVs. Use the project’s usual Slurm configuration when regenerating them. The following commands run from this benchmark repository on the workstation.

```sh
cluster=/mnt/covadongaflash/users/jaabell/three-way-benchmark
rsync -a explorer/prepare.py "jle:$cluster/web-explorer-prepare.py"
ssh jle "mkdir -p '$cluster/runs/web-explorer'"
ssh jle "/opt/slurm-24.11/bin/sbatch --wait -p new -N1 -n1 -c1 --mem=5G -t 00:12:00 --wrap='OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 /mnt/covadongaflash/software/bin/esmeralda-pvpython $cluster/web-explorer-prepare.py $cluster $cluster/runs/web-explorer/data'"
rsync -a "jle:$cluster/runs/web-explorer/data/" explorer/data/
npm ci --prefix explorer
node explorer/build.mjs
python -m http.server 8865 --bind 127.0.0.1 --directory explorer
```

Open `http://127.0.0.1:8865/dist/`. The output is a static folder. It needs HTTP, WebGL 2 for the 3D views, and a browser with `DecompressionStream`. All data, libraries, fonts, and logos are bundled in the folder. There is no runtime backend.

```sh
python explorer/tests/data.py
node explorer/tests/browser.mjs
tar -czf explorer/artifacts/beam-explorer.tar.gz -C explorer/dist .
```

Use `CHROMIUM_PATH` if Chromium is installed outside `/usr/bin/chromium`. Use `EXPLORER_URL` to exercise another hosted copy. The browser test writes screenshots to `explorer/artifacts`.

## Data and publication

- `prepare.py` maps exterior faces to source tetrahedron IDs and converts solver fields. It retains the T10 corner and midside nodes, checks fixed-end displacement, and verifies coordinate, field and load-step consistency over all accepted frames.
- `data/manifest.json` contains the model, theoretical reference, identifiers and decoded shapes. `*.bin.gz` files have little-endian arrays. The geometry block contains float32 XYZ, uint32 triangle vertex indices, uint32 triangle-to-surface-cell indices, and one-based cell IDs. Per-run ownership is uint16. Each load step stores float32 XYZ displacement followed by the ordered scalar arrays in the manifest. Zero is the undeformed initial state with zero response and the actual partition assignment.
- Displacement is shown at its nominal 1× scale by default. The surface shell is a piecewise planar drawing through the actual quadratic face nodes. Stress, strain and energy densities are four-point averages inherited from the ParaView export. The published files contain exterior fields for the seven cases and timing records for 180 CPU runs and 18 GPU pilots. The 237,600-element production mesh has no matched nonlinear result in this release.
- OpenSees and Kratos logos come from their project pages. The FEniCS logo is by Mattias Schläger, CC BY-SA 4.0. The Ladruño wordmark is from the author’s presentation assets. DM Sans and Instrument Serif are distributed under the SIL Open Font License. Three.js is MIT licensed. All required runtime assets are served locally.

Upload the complete `dist/` contents as a static app under a dedicated subdirectory on the blog. The HTML requests no indexing. This is direct-link hosting without a login. Keep the path off navigation, feeds and sitemaps until the video release.

Embedding example for the video release.

```html
<iframe src="https://joseabell.com/apps/beam-benchmark-e25983d5a2ab5975/" title="Esmeralda I-beam benchmark"
        width="100%" height="760" style="border:0" loading="lazy" allowfullscreen></iframe>
<p><a href="https://joseabell.com/apps/beam-benchmark-e25983d5a2ab5975/">Open the explorer full-page</a></p>
```

See [validation](VALIDATION.md) for the actual test results.
