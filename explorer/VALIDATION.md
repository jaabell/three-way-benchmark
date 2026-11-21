# Explorer validation

| Check | Status | Observed |
| --- | --- | --- |
| Conversion from original fields | PASS | Slurm job 9720 read seven real ParaView series. The smoke and fine surface meshes retain 6,810 and 47,330 nodes respectively. All 207 accepted frames passed finite-value, packing, mesh identity and clamped-node checks. |
| Numerical reference | PASS | The analytical plastic limit is 191.9791667 kN. At 29× gravity, the applied weight is 199.5840582 kN and the initial pair reads 78.839 mm downward. CPU timing records cover both 90-run campaigns, with three records per setting. |
| Release binary files | PASS | `python explorer/tests/data.py` checked binary lengths, pointer bounds, model extents, stress limits, rank IDs, and final tip values. The largest raw surface stress is 250.004865 MPa from the fine Kratos case. The shared stress color scale ends at nominal 250 MPa yield while the inspector retains the actual field value. |
| Partition export | PASS | Slurm job 9742 exported 4 coarse and 16 fine OpenSeesMP domains, with 14,864 and 110,184 display triangles. The validator checked index bounds, rank IDs and closed triangle-edge adjacency for every domain. Shared interfaces appear on both neighboring shells. |
| Fields and mesh density | PASS | Slides 4 and 6 use the same 13,616 coarse and 94,656 fine surface triangles. Checked the matching clamp camera, on-by-default mesh overlay, and Mesh only mode. The rasterized overlay fades edges that are too small to resolve at wide zoom. |
| Solver memory | PASS | Joined 180 CPU and 18 GPU-pilot job IDs with Slurm accounting. There are 108 comparable CPU rank RSS samples, 18 pilot host RSS samples and 6 nonzero GPU VRAM samples. The two-node PRRTE cases retain their job IDs and have no comparable peak rank RSS. |
| Local HTTP browser | PASS | Chromium with software WebGL ran the twelve-slide sequence. Verified surface-node visibility, the clamp cameras, solver-options filters and missing-memory states, gravity and partition animations, case and field selection, playback, plots, tables, GPU animation and Clean view. |
| Narrow viewport and iframe | PASS | Captured twelve 1920 × 1080 slides. Checked mobile at 390 × 844 and both field views in a 768 px test viewport with a 650 px iframe. No page-width overflow on mobile. |
| WebGL unavailable | PASS | With WebGL disabled, Chromium showed the static field image and retained the curves and timing tables. |
| Blog deployment | PASS | The same Chromium suite passed over HTTPS on the published subpath. HTML, JavaScript, CSS, manifest, fine geometry, and the default fine OpenSees frame matched local SHA-256 digests. The isolated Pelican output contained no link to the app in surrounding pages, feeds, search data or sitemap. The live page returns its `noindex` directive. |
| Direct files and other browsers | NOT TESTED | The deployed folder is intended for HTTP or HTTPS. Safari, Firefox and physical low-memory phones were outside this test. |

The opening slide loads logos, font and app code. Meshes, rank shells and result frames are fetched when their slides or steps are selected. Full-HD screenshots, the graphics ZIP, and the upload archive are in `explorer/artifacts/`.
