# Beam Benchmark Explorer

A standalone scientific viewer for a YouTube demonstration and direct-link blog access. The narrative moves through the beam and comparisons, rank scaling, and Esmeralda hardware. Two linked 3D views and one load cursor use each selected run’s accepted increments. Defaults show OpenSeesMP and FEniCSx on the fine mesh at 29× gravity with true-scale deformation and shared von Mises colors.

The seven field histories come from the Esmeralda ParaView series. The timing tables come from both validated CPU campaigns and the separate GPU pilots. Manifest provenance uses public-facing Slurm job IDs. The site includes the analytical Euler–Bernoulli reference derived from the nominal steel section.

Canonical coordinates and vectors are in metres with +x toward the free end and +z upward. The display maps these to (x, z, −y). Gravity multiplier is the animation axis, and force is the total weight in kN. Cell fields are the source four-point means, drawn on the exterior T10 facets with all midside nodes retained. Each exterior face is split into four triangles, with no volume clipping or spatial decimation. Float32 packing may change coordinates or displacements by at most 0.3 µm, and fields by at most two parts per million relative to their largest magnitude in a frame. Per-frame gzip files allow a responsive first load without a large monolithic download. Assets are same-origin and the target initial transfer is under 3 MB.

The site uses a static folder build and an HTTP static host. It exposes only results intended for the video, publishes no job directories or credentials, and uses local copies of required software assets. Direct-link placement excludes menus and feeds and requests no indexing. A static fallback covers WebGL failure.
