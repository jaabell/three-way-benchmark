# The I-beam benchmark

A [twelve-slide visual deck](SPEC.md) for the Esmeralda beam study. Use the slide picker, Previous/Next, or the left and right arrow keys. **Fullscreen** removes browser chrome. **Clean view** hides controls for recording. Press **H** or **Escape** to restore them. **Show surface nodes** marks the T10 corners with white squares and midsides with orange dots. The inset shows an actual exterior face, and **Midside only** hides the corners on the beam. On the paired field slide, choose **Stress** or **Strain**, then choose **Component**. Both views share the gravity step and color scale. The curve slide can show all seven runs or a filtered selection.

[Open the unlisted explorer](https://joseabell.com/apps/beam-benchmark-e25983d5a2ab5975/)

## Build and preview

The data preparation uses Esmeralda’s ParaView Python 6.2.1 and NumPy. It reads the seven archived VTK series and the benchmark CSVs. Use the project’s usual Slurm configuration when regenerating them. The following commands run from this benchmark repository on the workstation.

```sh
cluster=/mnt/covadongaflash/users/jaabell/three-way-benchmark
ssh jle "mkdir -p '$cluster/runs/web-explorer'"
rsync -a explorer/prepare.py explorer/partition_assets.py explorer/tensor_assets.py explorer/timing_assets.py "jle:$cluster/runs/web-explorer/"
ssh jle "/opt/slurm-24.11/bin/sbatch --wait -p new -N1 -n1 -c1 --mem=5G -t 00:12:00 --wrap='
  set -e
  export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
  cd $cluster/runs/web-explorer
  /mnt/covadongaflash/software/bin/esmeralda-pvpython prepare.py $cluster data
  /mnt/covadongaflash/software/bin/esmeralda-pvpython partition_assets.py $cluster data
  /mnt/covadongaflash/software/bin/esmeralda-pvpython tensor_assets.py $cluster data
'"
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

The recording graphics are in `explorer/artifacts/esmeralda-slides-1080p.zip`. The ZIP contains twelve PNGs at 1920 × 1080.

## Refresh CPU timing and memory

The CPU table uses exclusively node13 for 4, 8 and 16 ranks on both meshes. At 32 ranks it uses the original paired RoCE and TCP cases on node12 and node13. Each cell reports the median of three repeats in its output mode. Refresh the timing data and the matching Slurm job records without exporting the VTK series again.

```sh
python explorer/timing_assets.py results/esmeralda explorer/data
ids=$(PYTHONPATH=explorer python -c '
from pathlib import Path
from timing_assets import comparison, rows
reports = Path("results/esmeralda")
runs = [*comparison(reports, "measurements"), *rows(reports / "gpu-pilot-timings.csv")]
print(",".join(row["job"] for row in runs))
')
ssh jle "/opt/slurm-24.11/bin/sacct -n -P -j '$ids' -o JobIDRaw,JobName,State,NTasks,MaxRSS,TRESUsageInMax,NodeList" |
  python explorer/solver_memory.py results/esmeralda > explorer/src/assets/solver-memory.json.new &&
  mv explorer/src/assets/solver-memory.json.new explorer/src/assets/solver-memory.json
```

## Data and publication

- `prepare.py` maps exterior faces to source tetrahedron IDs and converts solver fields. It retains the T10 corner and midside nodes, checks fixed-end displacement, and verifies coordinate, field and load-step consistency over all accepted frames.
- `partition_assets.py` preserves the two sides of every inter-rank interface from the coarse 4-rank and fine 16-rank OpenSeesMP jobs. The explosion separates the closed rank shells by illustrative offsets.
- `tensor_assets.py` copies the signed XX, YY, ZZ, XY, YZ and XZ components from the saved VTK cell arrays. Stress is in MPa and strain is in millistrain. The shear strain values are tensor components εᵢⱼ, with engineering shear γᵢⱼ = 2εᵢⱼ. The browser fetches the companion float32 arrays when an additional component is selected. Both views use a zero-centered color scale shared across all saved runs and steps for that component.
- `solver_memory.py` verifies the CPU hosts against Slurm and joins solver-step memory with the same 180 CPU job IDs displayed on the timing slide, plus the 18 GPU pilots. Slurm `MaxRSS` describes the largest accounted task. The two-node jobs record PRRTE launcher tasks, and their per-rank solver RSS is unavailable.
- `data/manifest.json` contains the model, theoretical reference, identifiers and decoded shapes. `*.bin.gz` files have little-endian arrays. The geometry block contains float32 XYZ, uint32 triangle vertex indices, uint32 triangle-to-surface-cell indices, and one-based cell IDs. Per-run ownership is uint16. Each load step stores float32 XYZ displacement followed by the ordered scalar arrays in the manifest. Zero is the undeformed initial state with zero response and the actual partition assignment.
- Displacement is shown at its nominal 1× scale by default. The surface shell is a piecewise planar drawing through the actual quadratic face nodes. Stress, strain and energy densities are four-point averages inherited from the ParaView export. The published files contain exterior fields for the seven cases and timing records for 180 CPU runs and 18 GPU pilots. The 237,600-element production mesh has no matched nonlinear result in this release.
- OpenSees and Kratos logos come from their project pages. The FEniCS logo is by Mattias Schläger, CC BY-SA 4.0. The Ladruño wordmark is from the author’s presentation assets. Space Grotesk is distributed under the SIL Open Font License. Three.js is MIT licensed. All required runtime assets are served locally.

Upload the complete `dist/` contents as a static app under a dedicated subdirectory on the blog. The HTML requests no indexing. This is direct-link hosting without a login. Keep the path off navigation, feeds and sitemaps until the video release.

Embedding example for the video release.

```html
<iframe src="https://joseabell.com/apps/beam-benchmark-e25983d5a2ab5975/" title="Esmeralda I-beam benchmark"
        width="100%" height="760" style="border:0" loading="lazy" allowfullscreen></iframe>
<p><a href="https://joseabell.com/apps/beam-benchmark-e25983d5a2ab5975/">Open the explorer full-page</a></p>
```

See [validation](VALIDATION.md) for the actual test results.
