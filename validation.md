# Validation and delivery checklist

Use this as a release gate, not as a list to mark complete without evidence. Record PASS / FAIL / NOT TESTED / NOT APPLICABLE with the reason, command, expected result, observed result, and any artifact path. Use a project-specific `VALIDATION.md`.

## Scientific and content verification

- Inventory inputs, provenance, permission to publish and known missing data. Verify no secrets or restricted files are embedded in the distribution. All public data and externally loaded resources are disclosed.
- Recalculate or compare a representative set of important displayed values against source outputs; include input units and tolerance, actual differences and observed pass/fail. Check every headline metric definition and mapping from asset to UI. A few spot checks do not replace schema and range validation.
- Validate units, shape, dtype, finite values or explicit masks, index bounds, coordinate transforms, geometry orientation, time ordering, component signs, log-domain ranges, and consistent normalization across cases where claimed.
- For visual reduction verify that quantization, SVD/POD, mesh simplification and trace sampling meet the tolerances set in SPEC. Check critical extrema and local behavior, not only average error. Make any residual approximation visible to readers.
- Compare a representative plot or field with a reference figure or independent calculation. Verify measured and predicted series are labeled, correctly aligned and not misleadingly normalized. Verify uncertainty, limitations and schematic labels. Check citations and attribution.

## Build and distribution

- Run the full documented preparation/build using real input data. Missing required inputs must fail clearly. If partial data are intentionally allowed, report exactly what is missing.
- Verify the output directory has `index.html` and all required assets; no references to private absolute paths or machine-local resources; all generated markers resolved. Scan the actual distribution, not only source files.
- Test via HTTP under a nested path, e.g. start `python -m http.server 8765 --directory <parent>` and navigate to `http://localhost:8765/<dist-directory>/`. If an iframe test uses an additional wrapper, host it outside the deployable folder.
- For direct file operation, navigate to the exact built `file://` URL. No local fetch or external local-module imports should fail. If fully offline is promised, repeat in a fresh browser context with external networking disabled, separately from the file-origin test.
- Record build size, transfer size if measured, first-view latency plus measurement environment, and any large assets. Avoid claiming a fixed device performance without measurement. Test heavy scenarios, not just the initial cover. Check the final source archive can be rebuilt.

## Browser smoke test matrix (adapt as required)

| Test | Expected behavior |
|---|---|
| Initial load | Title, content and authentic first visual appear; no uncaught errors or failed required network requests |
| Every chapter/hash | Direct link, reload, next/previous, back/forward resolve correct narrative state |
| Rapid navigation | No stale fetch result, leftover animation, duplicated event listeners or broken selection |
| Filters/cases | All dependent geometry, metrics, charts, units and labels update together |
| Time controls | Play/pause, scrub, reset, endpoint and switch-case behavior are correct; plots and scene remain synchronized |
| Entity inspection | Pick known entity; verify expected ID, values and linked selection; repeat via keyboard-accessible control |
| Teaching inputs | Test defaults, boundaries, invalid inputs and known analytical values; resets behave correctly |
| Empty/missing data | An informative state appears, not zero-valued invented evidence |
| Desktop and mobile | Test e.g. 1440x900, 768x1024 and 390x844 CSS px; no clipped controls, unreadably tiny labels or accidental horizontal page overflow |
| Iframe | Test narrow width and ~650 px height; scrolling, navigation, focus, fullscreen fallback and assets work |
| Keyboard/touch | Key controls and focus indicators work without hover; text fields do not trigger chapter shortcuts |
| Reduced motion | No forced decorative animation/camera flight/tour; explicit physical playback remains available |
| Theme | If offered, contrast, legends, plot text and focus states work in both modes |
| WebGL unavailable | A useful explanation and alternative evidence are shown; the page does not simply go blank |
| Dependency failure | A recognizable fallback/error is visible rather than an endless spinner |

Prefer automated browser tests (Playwright or comparable) for navigation, controls, errors and failed requests. Capture representative desktop/mobile screenshots and inspect them visually. A screenshot is not proof that controls function or numerical results are valid. If browser automation is unavailable, run available static/data tests and document manual checks not performed; do not report visual correctness as confirmed.

## Blog handoff

Supply these artifacts as applicable:

- `dist/index.html`, plus required static assets if not a single file; a zip of `dist/` for upload.
- Editable source project, input inventory and rebuild commands. Do not include restricted or unnecessarily large raw data in the public zip.
- `README.md` with the purpose, chapters, dependencies, exact install/prep/build/test instructions, what to upload, deployment path, embedding example, data assumptions, missing inputs, online/offline status, and known problems.
- `VALIDATION.md` with real checks and remaining limitations. Optional preview screenshots and source attribution/license notices.

Upload contents of `dist/` to a dedicated folder (e.g. `/apps/<study-slug>/`) on a static host or the existing blog host. Use the existing deployment workflow if known. No deployment or public write without authorization. Only after the actual URL is known, set canonical metadata and generate any QR; verify it resolves. For cross-origin embedding check that the host permits framing (CSP `frame-ancestors` and `X-Frame-Options`) and the blog accepts iframes and required permissions. Never encourage disabling broad site security controls just to make embedding work.

Example snippet (replace the placeholder URL with the confirmed published URL; adapt height and permissions to the blog):

```html
<iframe
  src="https://example.com/apps/study-slug/"
  title="Interactive research explorer"
  width="100%"
  height="720"
  style="border:0; max-width:100%;"
  loading="lazy"
  allowfullscreen>
</iframe>
<p><a href="https://example.com/apps/study-slug/">Open explorer in a full page</a></p>
```

Do not require fullscreen for navigation. If an iframe is blocked or awkward on mobile, the standalone link remains useful. Set a meaningful, localized title. Confirm the final public page on the user's intended deployment only if accessible and authorized.

## Definition of done

A working, faithful, navigable static website exists at the reported output path, its scientific evidence is traceable, the source project and reproducible build are preserved, and the actual tests and limitations are documented. A plan, placeholder data, a pretty mockup, or an untested claim of offline compatibility does not meet this definition. If constraints prevent completion, deliver the working subset and identify the concrete blockers.
