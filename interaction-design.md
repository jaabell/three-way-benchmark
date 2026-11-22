# Interaction and visualization patterns

These patterns are optional building blocks. Choose only those that communicate the project's science. The original examples used a persistent 3D scene with chapters, and an indexed presentation with separate case views. Neither layout is mandatory.

## Guided explorer: persistent world, changing narrative

Use a single scene with semantic groups for entities, context geometry, annotations and visualized fields. Change camera framing, visible layers and selected entities instead of recreating the renderer per chapter. A declarative chapter description might look like this (pseudo-JavaScript):

```js
{
  id: 'response',
  title: 'Transient response',
  layers: ['model', 'deformed-shape'],
  camera: { preset: 'model-overview' },
  content: 'response-panel',
  clock: { start: 0, duration: responseDuration, unit: 's' },
  onEnter: resetResponse,
  onExit: cleanupResponse
}
```

On chapter entry, stop or cancel the old timeline/tweens, update the URL/navigation/panel, set visibility, establish the new selection and frame the camera. Start the new simulation clock at its actual initial time after arrival, if playback is enabled. Repeated quick navigation must not leave stale animations. Frame the object in the visible region, accounting for the text panel, and recompute on resize. Provide an explicit reset view and accessible non-3D fallback. Users should be able to inspect the scene freely without accidentally restarting a tour.

### Shared clocks and animated quantities

Keep physical time separate from render time. Use `requestAnimationFrame` with measured frame delta, bounded/clamped as appropriate, and make the time scrubber call the same update function as playback. Pause on document visibility change when practical; do not create a new loop on every chapter entry. Set the play button state consistently at the end. A changing case resets to its actual start; model switches can preserve time only if the time bases are compatible and the comparison calls for it. Label interpolation, normalized time, speedup and spatial exaggeration. Prefer changes to buffers, textures, shader uniforms or object transforms rather than full geometry rebuild at each frame. Pause or stop animation when out of view; release unused GPU resources.

### Inspectors and linked selections

Assign stable IDs to mesh objects, data points and series. A single selection action updates the inspector, highlight, chart series and metadata. For large meshes use raycasting against suitable pickable geometry or another tested picking strategy. Do not infer an element ID from visual order if data have been reordered. Render inspector text with safe DOM APIs. Provide a keyboard-accessible entity list or selector for equivalent inspection; hover can supplement but cannot be required. For small targets use reasonable touch hit areas. Selected objects must remain identifiable independently of color (outline, text, shape, etc.).

### Useful scene features

- Geographic context: use an overview map/globe only if location is relevant; include north, scale and coordinate conventions. Label schematic paths as schematic, not computed rays.
- Geometry: allow orbit/pan/zoom, reset, meaningful layers, orthographic or perspective presets when appropriate. Include colorbar, units and deformed/undeformed state.
- Scalar fields: use sequential or diverging colormaps suited to data; state fixed versus per-frame normalization. Distinguish unavailable data from zero; communicate clipped values and extrapolations.
- Modes, waves and transient response: synchronize scene and time-history cursor; for mode shapes label arbitrary normalization and amplification. Do not imply modal animation is a measured trajectory.
- Multi-case comparisons: ensure same coordinate frame, scales and units or explicitly note differences. A linked case selector should update every dependent view.

## Interactive presentation and comparison views

Use a chapter index grouped by concepts, methods, evidence and conclusion as appropriate. Each view should convey one core message with labels and context. For repeated cases implement one shared case template with title, scientifically supported metrics, common visuals, case-specific details and provenance. Reuse scale and axes conventions for direct comparisons; allow a toggle between common and local scales if needed and visibly explain the current one.

Linked data views might include a map/mesh, field image, summary plot and detail traces. Picking an entity from any view must have the same effect. Limit the number of simultaneously visible traces; make the selection clear and permit removal. Label experimental vs numerical series distinctly, and show comparison intervals when relevant. Never suggest full-resolution evidence if a screenshot or interpolated visual is the only available data.

## Teaching labs

Use sliders, inputs, presets and a reset to demonstrate genuine relationships in a mathematical or physical model. Show the equation or algorithm, units, valid range, assumptions and boundary/initial conditions. Implement the calculation, not a set of unrelated canned curves, unless clearly described as selecting precomputed cases. A slider must produce the correct corresponding result, including endpoints and invalid combinations. Validate with analytical limiting cases or independent reference outputs. If the example is schematic, label it visibly; don't mix it with measured or simulated research outcomes.

## Chart and UI implementation choices

SVG is a good default for moderate vector diagrams and plots; canvas is useful for dense traces or rapidly changing fields; WebGL is useful for genuine geometry and GPU-based animation. Use a plotting library or a small custom chart implementation according to need, not allegiance to a stack. Test hit testing, resizing and device pixel ratio. Provide accessible numeric summaries or tables for important chart data. Draw legends, axis labels, ticks and units even when space is limited. Scientific notation and log scales must be correct. Do not overwhelm a phone with parallel panels; adapt layout rather than shrinking text excessively.

For the visual system use CSS variables for background, text, surface, border, accent, font and scientific plot roles. Keep plots visually consistent between light and dark mode. If the research group already has conventions for observations, predictions and color maps, preserve them. Otherwise select a colorblind-friendly palette; distinguish series with dashes, labels or markers, not hue alone. Prefer system fonts or licensed locally bundled fonts in offline mode.

## Narrative navigation and embedding

A guided tour is useful for conferences but should be an explicit optional mode for blog visitors. A Start button may offer an Explore or Tour choice. Dwell times should allow reading, and user interaction stops automatic navigation. Provide an Exit Tour action; if the user hits back, do not automatically re-enter. Respect `prefers-reduced-motion` by replacing camera flights with cuts and disabling nonessential animation. Keep deep links stable across changes where possible. Do not use a keyboard shortcut while focus is in a control, and avoid capturing host-page behavior outside the explorer. Provide touch and keyboard equivalents for key actions.

Full-screen immersive UI should also work at an iframe height of about 600–800 CSS px and narrow width. Use available component height, not top-level screen assumptions. Avoid overlaying controls on important results. Ensure all content can scroll or reflow where necessary and don't trap scroll at the edge of an embedded view. Use semantic headings and status updates, and verify that chapter navigation moves focus or announces changes appropriately without disrupting playback. Include a text description and essential results when WebGL or JS is disabled, if the scientific material permits.
