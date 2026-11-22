---
name: scientific-web-explorer
description: Build polished, interactive, static scientific websites and research explainers from papers, Markdown, notebooks, simulations, datasets, figures, or an existing codebase. Use for blog-embeddable research explorers, conference companions, interactive posters, teaching demos, computational engineering visualizations, 3D model viewers, and data-driven presentations that require no backend. Produces a reproducible source project and a deployable index.html, not merely a summary or a mockup.
metadata:
  version: "1.0"
---

# Scientific Web Explorer

## Mission

Translate research or technical material into a compelling, self-contained browser experience. Let a reader understand the scientific question, inspect the evidence, change meaningful parameters or selections, and explore the results without installing specialist software. Build the actual working website, not a specification for someone else to implement, unless the user explicitly requests a specification only.

The primary audience is a curious blog reader; a specialist must also be able to find equations, units, assumptions, data provenance, limitations and references. Aim for the polish of a scientific exhibition, the fidelity of a research paper and the simplicity of a static website. This skill is domain-independent: do not assume every project needs a globe, seismic records, or a 3D scene.

## 1. Establish the brief and audit inputs

1. Read the supplied documents and relevant project files. Inspect the actual data schema, dimensions, units, representative values, geometry and figures. Locate existing publication metadata, plotting conventions, results and reusable code. Do not launch expensive simulations or notebooks with unknown side effects just to populate the site.
2. Determine the scientific question, intended audience, language, canonical title, authors, output directory, and deployment/embedding constraints from the request and repository. Use the existing site's branding if available. Otherwise use a restrained editorial theme and the user's language. Never invent authors, affiliations, URLs, or logos.
3. Identify what can be shown faithfully and which interactive ideas need unavailable data. Record source paths, public URLs or DOI, license/permission, version/date, units and transformations. Inspect public-data licensing before redistributing; never publish confidential inputs, raw credentials or restricted results. Remember that all client-side data can be downloaded.
4. Write a short `SPEC.md` in the project: purpose, audience, chapter map, selected UX pattern, inputs, data contract, coordinate/time conventions, performance budget, packaging mode, and missing inputs. Proceed with reasonable defaults; ask only when an unresolved decision blocks a meaningful or safe implementation. If sources are incomplete, produce a useful partial site and label unavailable components. Do not silently simulate missing evidence.

## 2. Select a narrative and interaction pattern

Choose one primary pattern based on the science, not on the format of the inputs:

| Pattern | When to use | Structure |
|---|---|---|
| Guided 3D explorer | Geometry, spatial processes, finite elements, field evolution | Persistent scene; chapters change camera, visible layers and explanatory panel |
| Interactive slide deck | Several concepts, methods or comparable research cases | Indexed chapters/slides; responsive plots, optional 3D scenes and case selectors |
| Scrollytelling article | Blog-first explanation, a paper with mainly 2D results | Semantic article, progressive graphics, inline interactions and optional sticky figure |
| Scientific lab | A small physical or numerical model that benefits from experimentation | Parameter controls, computed outputs, presets, reset, equations and validity limits |
| Comparison explorer | Parametric campaigns, experiments, model validation | Shared filters, aligned plots, linked selections, sortable results and detailed inspectors |

Hybrids are acceptable when they improve understanding. Use 3D only when depth, geometry or motion actually carries information. Prefer an interactive 2D plot to a decorative 3D scene. Do not reproduce a paper section by section by default.

Construct a sequence of roughly 5–12 chapters when appropriate, shorter for small studies:
- Opening: immediately show the topic, why it matters, and one compelling authentic figure or interactive scene. Include title, author/institution credits when known, and a clear Start/Explore action if using a cover.
- Context: explain the physical or conceptual problem, the scale, and the question being studied.
- Method: show inputs, assumptions, model, equations and workflow; explain each equation in words.
- Evidence: present the most meaningful results, comparison cases, validation and uncertainty.
- Implications: state what the evidence supports and what it does not; close with key findings, limitations, references and links to the paper/code/data when provided.

For each chapter define: `id`, title, one main message, supporting evidence, visual state, optional interaction, and entry/exit behavior. Make visuals lead and explanatory text support them. Readers should understand the main point without interacting; interaction should deepen understanding rather than unlock basic content.

## 3. Prepare trustworthy browser-ready data

Read [scientific data and packaging patterns](references/data-and-build.md) for numerical data, simulation assets or single-file publishing.

- Keep raw data, preparation scripts, generated data, UI source and deployment artifacts separate. Never manually edit generated output or use hardcoded copies of values that should be derived from source data.
- Use Python or the existing research toolchain for conversion, validation and derived metrics. Perform expensive computation offline as part of preparation. Small client-side calculations are welcome for teaching and filtering if equations, assumptions, ranges and tests are provided.
- Use a manifest and stable IDs to associate cases, geometry, time histories, labels, metrics, units and provenance. Document missingness; never convert missing values to zero. Distinguish measured, simulated, derived, interpolated and schematic content in visible labels and metadata.
- Use JSON for small assets; typed binary arrays, compressed textures and validated reduced-order representations for large numerical data. Only reduce display resolution; never recompute reported metrics from display-decimated data unless appropriate and disclosed.
- Define one canonical coordinate system, origin, units, sign conventions and time axis before exporting spatial or temporal data. Transform to visualization coordinates in one place. Label deformation/exaggeration factors and time speedups.
- Export a validation report with counts, ranges, units, reference checks, missingness, approximation errors and asset sizes. Required invalid data fails preparation; optional missing data produces a clear warning and an honest fallback. Never display invented results as evidence. Clearly label synthetic teaching examples.

## 4. Implement the website

Prefer simple HTML, CSS and JavaScript (ES modules when useful), a minimal Python build, and no runtime server, login, database, API keys, or hosted computation. Use an existing project stack if justified; any build tooling must still emit static deployable assets. Avoid adding dependencies for features native to the browser. Pin versions; use reputable libraries such as Three.js for genuine 3D and KaTeX for equations, if needed. Do not introduce a heavy framework solely to render a few views.

Read [interaction and visualization patterns](references/interaction-design.md) for 3D scenes, animations, linked charts or guided tours.

### Visual and editorial standards

- Use a coherent high-contrast palette, type hierarchy, whitespace and CSS design tokens. Default to off-white content panels, ink/navy text, one restrained accent, optional dark mode for visualization-heavy pages. Maintain the research group's existing semantic plot colors where available. Do not impose generic dashboard cards, gradients, glassmorphism or ornamental charts.
- Every quantitative chart has units, meaningful labels, a legend when needed, an appropriate scale and a source/context caption. Compare like with like using consistent ranges and conventions; diverging fields need a meaningful midpoint. Log scales must be valid. Include uncertainty when available or explicitly say it was not quantified.
- Use real research visuals and purposeful diagrams; not decorative imagery posing as results. Prefer vector text/graphics for explanatory diagrams. Use meaningful tooltips and inspectors rather than unlabeled gestures.
- Write concise, technically precise text. Define jargon at first use. Preserve mathematical notation, avoid exaggerated claims, and make the distinction between the original research and the site's illustrative additions clear.

### Navigation, interaction and state

- Use a visible chapter index or article navigation, previous/next where applicable, stable `#chapter-id` deep links, and a clear way to return to the beginning. Browser back/forward must work; direct links should open the correct chapter.
- Keep state centralized: chapter, selected case/entity, time, playback, filters, theme and camera mode when relevant. All linked plots, metrics and scene objects must update consistently. Reuse one component for comparable cases rather than copy-pasting.
- For time-dependent views provide Play/Pause, reset, time scrubber, time units and playback speed if meaningful. Synchronize charts and scene to one simulation clock; prevent multiple competing animation loops. Reset time upon entering a different animation or changing an incompatible case; pause/resume preserves the current time.
- A guided tour is optional and opt-in by default. It must pause on manual interaction, be stoppable at any moment and never steal focus. Respect reduced-motion settings.
- Make every visible control functional, with correct state, bounds and disabled/empty states. Provide useful defaults, presets or reset. Avoid dead buttons, fake data and decorative controls.

### Blog embedding and accessibility

- Treat the site as a standalone application that can also live inside an iframe at an arbitrary blog subpath. Use relative paths; do not depend on a root URL, parent DOM, top-level navigation, or viewport width of the host blog.
- Responsive layouts must work at a narrow phone width, tablet, desktop and typical blog iframe size. For spatial scenes use a collapsible side panel on desktop and a non-obstructing bottom sheet or stacked view on mobile; ordinary articles should reflow normally.
- Use semantic HTML, accessible names, visible keyboard focus, sensible tab order, usable touch targets, contrast and text alternatives for visual-only evidence. Provide meaningful fallback content if WebGL is unavailable; do not rely on hover, drag, color or animation alone. Respect `prefers-reduced-motion`; don't hijack keyboard events in input fields or trap page scrolling.
- Avoid analytics, trackers, cookies and network calls unless required and explicitly permitted. Public third-party assets and dependencies must be disclosed. Include page title, description, lang, and social metadata if suitable; canonical URL and QR only if the final public URL is known. Provide a full-page link alongside the iframe in the host blog snippet.

## 5. Optimize, build and document

Default target: an `index.html` that opens directly from disk with double click and deploys at any static URL. Package CSS, application JavaScript, prepared dataset and local essential images into the file wherever practical. A pinned CDN library is acceptable if disclosed, but this is not offline operation. When offline support is requested, vendor required libraries/fonts/assets into the distribution and test with networking disabled. Do not rely on local `fetch()` or module file imports for the single-file artifact.

For heavy projects, choose a static folder with lazy-loaded, same-origin data assets rather than sacrificing scientific fidelity or responsiveness. If direct double-click cannot be supported, say so and supply a local static server command. Preserve consistent behavior across development and publication builds.

As a starting budget aim for <5 MB total transfer for small sites, <15 MB for dense scientific explorers, and a responsive first view. These are project targets, not universal limits. Profile, measure and document exceptions. Use scoped assets, decimated display meshes, typed arrays, compressed images, lazy rendering and bounded active plots. Avoid doing expensive work in every animation frame. Measure final HTML size as well as actual transfer size when hosted.

Suggested project tree (simplify for small projects; adapt existing layouts):

```text
research-explorer/
  SPEC.md                 # brief, data conventions, story, constraints
  README.md               # setup, build, test, deploy, embed, limitations
  prep/                   # reproducible data preparation and validation
  data/                   # generated browser assets and manifest
  src/                    # HTML template, CSS, JS, local images
  tests/                  # data and browser checks as feasible
  build.py                # deterministic packaging entry point
  dist/index.html         # publishable entry point; extra assets if needed
  VALIDATION.md           # evidence checks and browser test results
```

Preserve the source project. Use UTF-8 everywhere, deterministic inputs and output order, explicit dependencies and reproducible commands. Escape embedded data safely; do not concatenate untrusted HTML into a script. Include attribution and license notices in the visible site and distribution where applicable. Avoid overwriting an existing public version unless requested.

## 6. Verify before claiming completion

Read [validation and delivery](references/validation.md) and apply the relevant checks. At minimum:

1. Rebuild from documented inputs; validate datasets, check important displayed numbers with their source, and verify scientific sign/scale/geometry conventions.
2. Serve the actual distribution with a local static server and test in a browser, using browser automation (e.g. Playwright) if available. Also open the final file using `file://` when single-file operation is promised. Check console errors, failed requests, chapter deep links and controls. Test embedded subpath behavior.
3. Exercise the real interactions: change a case/parameter, select an entity, scrub and play time, inspect labels/metrics, reset, and navigate back. Test desktop and mobile widths, keyboard access, and the smallest meaningful viewport. If relevant, test WebGL failure and reduced motion. Inspect screenshots for overlaps or unreadable graphics; don't settle for a successful build alone.
4. Record actions actually run, measured sizes, expected/observed values, pass/fail/untested cases and any remaining caveats. Fix failures within scope. Never claim browser, device, offline, or hosting tests were passed if not performed.

## 7. Deliver

Return the working deployable site, a ZIP of the distribution if useful, the editable source project, README/build instructions, and validation report. Point directly to the entry file and identify what to upload. Include a ready-to-copy iframe embedding example using the confirmed public URL or an explicitly marked placeholder. Provide a brief summary of the experience and decisions, missing data, required internet access, known limitations, and actual test status. Do not publish to the user's blog or hosting account unless explicitly authorized.

### Example requests

- "Turn this paper and its HDF5 simulation outputs into an interactive research companion for my blog."
- "Make a guided 3D explorer of this FEM model with a deformation timeline, stress fields and an element inspector."
- "Create a static interactive explanation of this constitutive model with a parameter lab and stress paths."
- "Present these experiments as comparable cases with linked plots, uncertainty and a reproducible build."

All are instances of the same workflow. Tailor the experience to the science, available evidence, audience and publication constraints.
