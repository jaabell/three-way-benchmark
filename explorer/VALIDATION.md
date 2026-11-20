# Explorer validation

| Check | Status | Observed |
| --- | --- | --- |
| Conversion from original fields | PASS | Slurm job 9720 read seven real ParaView series. The smoke and fine surface meshes retain 6,810 and 47,330 nodes respectively. All 207 accepted frames passed finite-value, packing, mesh identity and clamped-node checks. |
| Numerical reference | PASS | The analytical plastic limit is 191.9791667 kN. At 29× gravity, the applied weight is 199.5840582 kN and the initial pair reads 78.839 mm downward. CPU timing records cover both 90-run campaigns, with three records per setting. |
| Release binary files | PASS | `python explorer/tests/data.py` checked binary lengths, pointer bounds, model extents, stress limits, rank IDs, and final tip values. The largest raw surface stress is 250.004865 MPa from the fine Kratos case. The shared stress color scale ends at nominal 250 MPa yield while the inspector retains the actual field value. |
| Local HTTP browser | PASS | Chromium 152 on Linux, with software WebGL, loaded the shipped build under `/dist/`. Seven case selectors, all seven field options, the keyboard camera, element inspection, timeline, charts, timing filters, presentation view, and chapter navigation worked without an uncaught error or HTTP failure. |
| Narrow viewport and iframe | PASS | Desktop 1440 × 1000 and mobile 390 × 844 screenshots were inspected. A 768 px test viewport with a 650 px iframe loaded both views. No page-width overflow on mobile. |
| WebGL unavailable | PASS | With WebGL disabled, Chromium showed the static field image and retained the curves and timing tables. |
| Blog deployment | PASS | The same Chromium suite passed over HTTPS on the published subpath. HTML, JavaScript, CSS, manifest, fine geometry, and the default fine OpenSees frame matched local SHA-256 digests. The isolated Pelican output contained no link to the app in surrounding pages, feeds, search data or sitemap. The live page returns its `noindex` directive. |
| Direct files and other browsers | NOT TESTED | The deployed folder is intended for HTTP or HTTPS. Safari, Firefox and physical low-memory phones were outside this test. |

The release totals 93.8 MB on disk, with about 3.07 MB of initial assets at the default fine-mesh comparison before HTTP transport compression. Later frames are fetched when selected. Preview screenshots and the upload archive are in `explorer/artifacts/`.
