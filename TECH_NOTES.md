# vacuum_quad_engine — Tech Notes

Single source of truth for what this pipeline uses and why. Update this
file the moment anything changes — a library swap, a threshold rethought,
a module renamed/split. Never let it go stale.

## Primary objective (recap — see plan file for full text)

No fixed face-count target/budget anywhere. Zero feature loss is the hard
constraint; minimum face count under that constraint is the goal. Output
must read as genuine Tripo-level anisotropic, structured, quad-dominant
flow — stretched quads on flat regions, triangles only as topological
valves, no unnecessary edges. Must generalize to arbitrary AI-generated
meshes, not just the validation corpus.

## Binaries / external tools

| Tool | Path (this machine) | Used for | Notes |
|---|---|---|---|
| Blender | `/Applications/Blender.app/Contents/MacOS/Blender` (5.2.3 LTS) | All mesh I/O, bmesh operations, curvature-adjacent geometry ops, rendering previews | Invoked via `--background --python-expr`/`--python <script>` subprocesses, same pattern as tripo_smart_engine |
| Instant Meshes | `/Users/bhargavreddy/Downloads/bhargav's one/tools/Instant Meshes.app/Contents/MacOS/Instant Meshes` | Primary field-aligned quad remesher (`-D -S 1 -d -b -r 4 -p 4 -c <deg> -f <hint>`) | GUI mode has repeated crash logs in `~/Library/Logs/DiagnosticReports` (2026-10-31) — CLI batch mode (`-o`, no GUI) tested clean 2026-11-01. Always invoke headless/batch; never open its GUI. |
| quadriflow | `vacuum_quad_engine/bin/quadriflow` | Fallback field-aligned remesher if Instant Meshes misbehaves on a given asset | Already proven stable in `tripo-logic-approach-v2` |

`core/config.py` resolves both and picks `DEFAULT_REMESH_BACKEND` automatically
(prefers Instant Meshes when present). `remesh.py` must support both and
allow a per-component fallback to quadriflow if Instant Meshes fails/crashes
on that component.

## Python libraries

| Library | Version (this machine) | Used for |
|---|---|---|
| trimesh | 5.0.0 | Mesh loading/validation outside Blender, watertight/winding checks, proximity/deviation sampling |
| numpy | 2.5.1 | Array math throughout |
| libigl (`igl`) | available | Per-vertex curvature (principal/Gaussian curvature) in `curvature.py` |
| bpy | via Blender 5.2.3 | All mesh-editing operations (decompose, remesh I/O, dissolve, darts, caps, reproject) |

## Module map (`core/`)

| Module | Purpose | Lineage |
|---|---|---|
| `config.py` | binary paths, tunables | new (done — T0) |
| `io_blender.py` | FBX/GLB/OBJ import/export via bpy, per-object stats | new, reuses tripo_smart_engine's `decomposer.py` import/export flag patterns (`forward_axis='NEGATIVE_Z', up_axis='Y'`) |
| `curvature.py` | per-vertex curvature field on the dense input mesh | new — none of the 3 prior efforts have this |
| `decompose.py` | split mesh into connected components (NOT joined into one) | new — direct fix of tripo_smart_engine's `decomposer.py` joining everything into 1 object |
| `sizing.py` | per-component curvature-integrated target_faces HINT (not a budget) | new, formula user-confirmed: `h(v) = clip(sqrt(epsilon/max(kappa,floor)), h_min, h_max)` |
| `remesh.py` | Instant Meshes (or quadriflow) invocation, once per component | adapted from tripo_smart_engine's `remesher.py`, made per-component |
| `protect.py` | continuous curvature-weighted edge protection/cost, LOCAL per-component micro-feature baseline | adapted from `ribbon_engine.py`'s Step 1 protection mask; fixes its global-median bug |
| `dissolve.py` | transverse-loop + straight-slat dissolution driven by continuous cost | ports `trace_full_transverse_loop`/`trace_straight_loop` from `ribbon_engine.py` near-verbatim, replaces its fixed 3°/18° tier gating |
| `darts.py` | coplanar triangle-pair / diamond-dart merging | ports `apply_diamond_dart_adapters` from `ribbon_engine.py` |
| `caps.py` | parallel-chord quad caps for near-planar circular boundaries | ports the bevel-ring + chord-strip construction from `burger_stand_retopo.py` |
| `reproject.py` | CAD-surface shrinkwrap onto original dense mesh | ports Step 3.5 from `ribbon_engine.py` |
| `audit.py` | forensic metrics (quad%, valence-4%, boundary edges, aspect ratios) | ported as-is from tripo_smart_engine's `audit.py` (already verified accurate) |
| `pipeline.py` | orchestrates all of the above | new, modeled on tripo_smart_engine's `pipeline.py` staging |

## Thresholds and their scale-dependence

| Threshold | Value | Scale-independent? |
|---|---|---|
| `CREASE_DEG` | 18.0° | yes (angle) |
| `TIER1_FLAT_DEG` | 3.0° | yes (angle) — used as a *continuous cost input*, not a hard tier boundary, per the Primary objective |
| `MICRO_FEATURE_CURVE_DEG` | 12.0° | yes (angle) |
| `MICRO_FEATURE_AREA_FRAC` | 0.15 (fraction of LOCAL per-component median face area) | yes (relative fraction, and now local instead of global — fixes the jade-sword-hilt bug) |
| `DOME_SADDLE_DEG` | 28.0° | yes (angle) |
| `COPLANAR_DART_DEG` | 24.0° | yes (angle) |
| `PLANAR_STRAIGHTEN_DEG` | 3.0° | yes (angle) |
| weld distance | *(to be set in `io_blender.py`)* | must be `k * bbox_diagonal`, never an absolute unit — per Generalization requirement |
| BVH outward-normal ray-hit distance (ribbon_engine had a hardcoded 0.35 units) | *(to be re-derived)* | must be `k * bbox_diagonal` when ported, NOT kept as a fixed 0.35 |

## Test corpus

- `vacuum_quad_engine/assets/inputs/`: `000-004.glb`, `Beetle_Car.glb`,
  `furn16_woodenrack_raw_854k.glb`, `jade_sword.glb`, koala glb,
  `testsample1_raw_860k.glb` (sofa), `c1.obj`, `tripo_futuristic_robot.fbx`,
  `tripo_robot_reference.fbx`.
- `/Users/bhargavreddy/tripo-smart meshes/*.fbx`: 8 genuine Tripo exports
  (wooden dresser, futuristic robot, smiley face, t-rex, cute dragon,
  fantasy character, stylized female, parumala_thirumeni) — used for
  feature/flow comparison against known-good reference wireframes.
- Held out from threshold-tuning (generalization check, per plan):
  `000.glb`-`004.glb`, `Beetle_Car.glb`, koala glb, `c1.obj` (not
  Tripo-sourced, not used to derive any threshold above).

## Known reference stats (measured this session, for comparison only — not targets)

| File | Quad% | Valence-4% | Islands |
|---|---|---|---|
| wooden dresser | 81.6% | 85.6% | 36 |
| futuristic robot | 65.2% | 69.4% | 88 |
| smiley face | 89.2% | 91.2% | 12 |
| t-rex | 85.2% | 89.2% | 51 |
| cute dragon | 89.3% | 86.8% | 4 |
| fantasy character | 59.5% | 63.8% | 29 |
| stylized female | 92.9% | 91.9% | 6 |
| parumala_thirumeni | 71.6% | 74.6% | 3 |

## Verification discipline (user instruction, 2026-11-01)

"Make sure to output of every step thoroughly before moving to next step,
cause later we should not be wondering where the problem is coming from."
Applies for the rest of implementation: every task gets an actual visual
or data-level check before being marked done in PROGRESS.md, not just an
aggregate number. T6 is the example — 68% hard-protected looked alarming
as a bare number, but a rendered wireframe immediately showed it was
correct (tube rings vs. rail lengths). Keep doing this: render, don't just
count.

## Real bugs found via generality testing (2026-11-01)

Testing `remesh.py` across the dresser AND jade_sword corpora (not just the
one asset originally used to build it) surfaced two genuine, previously
invisible failure modes — exactly why every step gets rendered/measured
before moving on:

1. **Instant Meshes can silently fragment a solid single-island component
   into hundreds of disconnected shrapnel pieces**, with exit code 0 and a
   valid-looking OBJ written — not caught by "did the subprocess succeed."
   Confirmed concretely on dresser `comp0003` (a divided open-top box): 1
   island in, 407 islands out at the real target_faces hint, STILL 20+
   islands out even forced down to `target_faces=50`, so it's a genuine
   geometry-handling failure, not a density/upsampling artifact. Fixed in
   `remesh.py`: `count_islands()`/`is_fragmented()` (via trimesh
   `mesh.split`) now gates every backend's output; a fragmented result is
   rejected and the other backend is tried; if BOTH backends fragment, the
   component is passed through UNCHANGED (`backend: "passthrough_unremeshed"`)
   rather than shipping shrapnel — a strictly safe degradation under the
   Primary objective (zero feature loss outranks face reduction).
1b. **quadriflow also has its own distinct failure mode**: an internal
   solver error (`wrong init 56 58!` printed to stdout) that aborts WITHOUT
   writing the output file, but still exits with return code 0 — not a
   crash signal, not a nonzero exit, just silently no output. Confirmed
   unrelated to the space characters in Tripo's own filenames (reproduced
   identically against a copy at a space-free path). `remesh_quadriflow`'s
   existing `ok = rc==0 and os.path.exists(out_obj) and getsize>0` check
   already catches this correctly (file-existence check, not exit-code
   trust) — flagging only so a future reader doesn't "fix" the exit-code
   check and reintroduce a silent failure.

Net effect on the full corpus so far: dresser 11/36 (31%) and jade_sword
9/107 (8%) of components end up on `passthrough_unremeshed` — both real
field-aligned remeshers (Instant Meshes AND quadriflow) failing on the
same small/oddly-shaped piece often enough to matter, not a rare edge
case. This is an acceptable, SAFE outcome per the Primary objective (zero
feature loss beats face reduction), but a meaningfully high rate — worth
revisiting in a later pass (e.g. retry with a different seed/flag set
before giving up, or a simple quadric-decimation quad-pairing as a third
automatic backend) rather than accepting it as a ceiling. `pipeline.py`
(T11) and `darts.py`/`caps.py` (T8) must treat passthrough (still-
triangulated) components as a normal, expected input, not an error case.

2. **Instant Meshes is unreliable on small/low-target-face components.**
   On jade_sword's 107 (small, ornamental) components, Instant Meshes only
   produced a clean result on 5/107 — the rest fell back to quadriflow (93)
   or passthrough (9, where even quadriflow fragmented). On the dresser's
   larger components it was mostly fine. Working hypothesis: Instant
   Meshes' field solver becomes unstable at very low absolute target face
   counts (teens-to-low-hundreds) regardless of geometry. Not yet changed
   `DEFAULT_REMESH_BACKEND` selection logic to account for this — the
   automatic per-component fallback already in `remesh_component` handles
   it correctly either way, just worth knowing the fallback is doing real,
   frequent work on small-part-heavy assets, not just a rare safety net.

## T7 dissolve: area has no single correct value for non-planar geometry

Key lesson, worth remembering for any future mesh-simplification work in
this project: once a merged face is non-planar (the normal case for any
curved real component, not an edge case), "surface area" stops being a
well-defined invariant — different valid computation methods (bmesh's
Newell-projection `calc_area()`, a from-scratch vertex-fan triangulated
sum, trimesh's own triangulation) can legitimately disagree by 30%+ on the
exact same geometry, independent of whether anything was actually lost.
The only trustworthy, planarity-independent invariant for a dissolve
operation (which never moves a vertex) is that boundary-edge count can
never increase. Area is now tracked as an informational stat in
`dissolve.py`'s output, not a pass/fail gate — verified instead by the
boundary-edge check plus a direct render/watertight spot-check.

## Important: test inputs must be DENSE/raw, not Tripo's own clean output

The 8 FBX files in `/Users/bhargavreddy/tripo-smart meshes/` are Tripo's
OWN finished, already-optimized low-poly exports — they are the TARGET to
match, not representative INPUT for this pipeline. Feeding one back through
decompose→size→remesh→dissolve re-processes an already-minimal mesh, which
is a real but out-of-scope stress test: the first full pipeline run on
`wooden dresser 3d model.fbx` produced LOWER quad%/valence-4% (67.94%/
50.2%) than the input already had (81.6%/85.6%) — not because the engine
regressed, but because there is very little genuine curvature-driven
density variation left to exploit in an already-clean reference mesh, and
re-remeshing it at a hint derived from its own (already low) face count is
a different problem than the intended dense-AI-scan-to-clean pipeline. Any
future quality comparison must run on a genuinely dense/raw input
(`furn16_woodenrack_raw_854k.glb`, the dense per-component OBJs under
`assets/inputs/`, or the dense pre-Tripo source of any reference asset) and
compare the RESULT against the Tripo reference — never feed the reference
itself back through the pipeline as if it were raw input.

## Real bug: sizing.py's target_faces_hint formula (found via raw single-blob asset test)

`target_faces_hint = area / mean(h)^2` (a SIMPLE, unweighted mean of the
per-vertex target edge length h) catastrophically under-sized a genuinely
raw, single-connected-component dense asset: the 854k-tri wooden rack GLB
(no pre-segmented parts, unlike Tripo's own already-segmented exports)
collapsed to 133 faces with every leg missing. Root cause: an unweighted
mean of h is dominated by whichever region has the most VERTICES, which on
a roughly-uniform dense scan is the large flat panels — a thin, high-
curvature leg barely moves the mean even though it's exactly the region
needing a small h. Fixed in `sizing.py` to the correct AREA-WEIGHTED
INTEGRAL: `sum_i(local_vertex_area_i / h_i^2)`, giving each region face
budget proportional to its OWN area and curvature, not diluted by vertex
count elsewhere. Confirmed fix: rack target_faces_hint 984 → 43,423;
final output 133 → 3,431 faces with all 4 legs and the divider/shelf
structure restored (visually confirmed, see `rack_fixed_HONEST.png`).

## Methodology fix: honest (non-triangulated) rendering

`trimesh.load(..., force='mesh')` always triangulates every face
internally, including clean quads and clean flat n-gons — so a genuinely
clean quad-dominant mesh and a real triangle fan render IDENTICALLY via
`Poly3DCollection(v[f])` (both show a diagonal through every face). This
caused a real misdiagnosis earlier this session (the 002.glb "chaotic
triangle fan" claim, later walked back). All visual QA from here on uses a
custom OBJ loader that preserves real face sizes and feeds variable-length
polygons directly to `Poly3DCollection` — no forced triangulation. Any
future render/screenshot MUST use this method, not `trimesh.load(...,
force='mesh')`, or it will misrepresent true quad/n-gon cleanliness.

## 8-asset Tripo reference benchmark (averaged, not single-asset)

Per user request, built `benchmarks/tripo_reference_average.json` from
`core/audit.py` run on all 8 real Tripo FBX references (not just one).
MEDIAN is the primary comparison metric (the wooden dresser reference has
one extreme 1768:1 outlier sliver quad that badly skews the mean for
aspect ratios). Median benchmark: quads_pct 83.38%, valence_4_pct 86.21%,
triangles_paired_pct 83.07%, aspect_median 1.735, aspect_90th 3.63,
aspect_max 28.42, parallelism_median 0.993, boundary_edges 129,
non_manifold_edges 8.5, islands 20.5. Per-asset raw numbers are the
sibling JSON files in `benchmarks/`.

## Log

- 2026-11-01: T0 complete. `config.py` resolves Blender 5.2.3, Instant
  Meshes (found at a non-standard path under Downloads, CLI-tested
  working), and `bin/quadriflow`. `DEFAULT_REMESH_BACKEND = instant_meshes`.
- 2026-11-01: T1 complete. `io_blender.py` verified against the reference
  stats table exactly (dresser 81.58%/36 islands, robot 65.2%/88, dragon
  89.3%/4).
- 2026-11-01: T2 complete. `curvature.py` — confirmed Blender's bundled
  python (3.13, under `/Applications/Blender.app/.../Resources/5.2/python`)
  has neither `igl` nor `trimesh`; curvature always runs as a separate
  system-python3 subprocess. `igl.principal_curvature(V, F, radius, useKring)`
  returns `(PD1, PD2, PV1, PV2, bad_vertices)` — 5 values, not 4 as first
  assumed; `F` must be `int64`. `kappa = max(|PV1|, |PV2|)` used as the
  dominant curvature magnitude feeding `sizing.py`'s `h ∝ sqrt(eps/kappa)`.
  Verified visually on jade_sword.glb and the Tripo robot.
