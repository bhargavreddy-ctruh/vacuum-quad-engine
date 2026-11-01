# vacuum_quad_engine — Progress

Status legend: `[ ]` not started, `[~]` in progress, `[x]` done.
Updated at the start and end of every task — never batched at session end.

- [x] **T0 — Bootstrap & tracking docs** (2026-11-01): `core/config.py`
      created, resolves Blender 5.2.3 LTS, Instant Meshes (non-standard
      path under `~/Downloads/.../tools/`, CLI batch mode tested clean),
      `bin/quadriflow`. `TECH_NOTES.md` and this file created.
- [x] **T1 — I/O layer** (2026-11-01): `core/io_blender.py` created
      (import/export FBX/GLB/OBJ via bpy, per-object stats, island count via
      vertex flood-fill, `bounding_box_diagonal()` for scale-derived
      tolerances elsewhere). Verified: dresser/robot/dragon FBX stats
      (quad%, islands) exactly match the session's already-measured
      reference table; 854k-tri wooden-rack raw GLB loads in ~2s
      (1 island, 100% tris, as expected for the raw unsegmented scan).
- [x] **T2 — Curvature field** (2026-11-01): `core/curvature.py` created
      (libigl `principal_curvature`, runs under system python3 — confirmed
      Blender's bundled python lacks igl/trimesh, so this always runs as
      its own subprocess, fed an intermediate OBJ for FBX inputs via
      `io_blender.py`). Fixed an API-signature bug (returns 5 values,
      `bad_vertices` list, not 4; faces need int64). Verified by eye on
      jade_sword.glb (flat blade = dark, ornamental hilt = bright) and
      robot.obj (panel-line joints bright, flat wing dark) — curvature
      correctly isolates detail from flat regions.
- [x] **T3 — Decomposition** (2026-11-01): `core/decompose.py` created —
      join-then-immediately-loose-separate (end state is always N separate
      component objects/OBJs, never a joined mesh carried into remeshing;
      the join is only a mechanism for bpy's `separate(type='LOOSE')`, not
      the tripo_smart_engine bug it fixes). Each component exported as its
      own OBJ + a JSON manifest (path, stats, bbox_diagonal per component).
      Verified: dresser=36, robot=88 components, exactly matching measured
      island counts.
- [x] **T4 — Per-component sizing** (2026-11-01): `core/sizing.py` created
      (`h = clip(sqrt(eps/max(kappa,floor)), h_min, h_max)`, all three
      scaled from the WHOLE ASSET's bbox diagonal so components share
      consistent units; integrated `target_faces_hint = area/mean(h)^2`,
      explicitly a hint for the remesher, never a cap). Verified on the
      dresser's 36 components: a large flat component (area 0.668,
      kappa_median 3.6) got density ~2,886 faces/unit-area; a small
      high-curvature component (area 0.00067, kappa_median 239) got
      ~220,898 faces/unit-area — curvature-driven, not size-driven,
      confirming no per-asset special-casing is needed.
- [x] **T5 — Remesh** (2026-11-01, revised after generality testing):
      `core/remesh.py` — per-component Instant Meshes / quadriflow, with a
      real fragmentation guard (`is_fragmented` via `trimesh` connected-
      component count) added after the FIRST pass of this task looked
      clean on paper (rc=0, file written) but visual inspection caught
      Instant Meshes silently shattering dresser comp0003 into 407
      islands from a 1-island input. Both backends now gated by actual
      output quality, not subprocess exit codes; a component where BOTH
      backends fail falls back to `passthrough_unremeshed` (original
      geometry kept exactly, zero feature loss, just not reduced).
      Generality-tested on dresser (36 comps: 1 IM, 24 quadriflow, 11
      passthrough) and jade_sword (107 comps: 5 IM, 93 quadriflow, 9
      passthrough) — real, non-trivial fallback usage on both assets, not
      a rare safety net; see TECH_NOTES for the two distinct underlying
      failure modes found (IM fragmentation; quadriflow's silent
      `wrong init` solver abort).
- [x] **T6 — Protection mask** (2026-11-01): `core/protect.py` created —
      hard-protect (boundary, true crease >=18°, dome/saddle pole
      vertices) + a continuous finite cost (base dihedral angle + a smooth
      micro-feature bonus using this component's OWN local median face
      area, never a global one) for everything else. Found and fixed a
      real bug: face normals needed `bmesh.ops.recalc_face_normals` right
      after import before ANY angle-based test, or Instant Meshes'
      winding produces false deviation readings (this did not change the
      actual numbers below, confirming winding was already consistent
      here, but is a correctness requirement that must stay in place for
      other assets). Measured on dresser comp0001: 68% hard-protected.
      VISUALLY CONFIRMED CORRECT, not a bug (`render_protect_debug.py`,
      `comp0001_closeup.png`): this component is a thin rounded tube/rail
      bent into a rectangle (a handle/pull). The red (protected) edges are
      exactly the tube's cross-section rings, correctly protected all the
      way around since a round tube is genuinely curved everywhere in that
      direction; the colored (free, finite-cost) edges are exactly the
      lengthwise rails along each straight run, correctly left free for
      T7's straight-slat dissolution to collapse. This is the textbook
      anisotropic pattern the whole engine targets — confirmed by eye
      before trusting the aggregate percentage.
- [x] **T7 — Dissolution** (2026-11-01, found and fixed a real bug via
      real-asset testing): `core/dissolve.py` — ported
      `trace_full_transverse_loop`, driven by protect.py's continuous cost
      (lowest-cost/flattest loops dissolved first each pass) instead of
      fixed tiers. Synthetic flat 10x6 grid self-test: 60→1 faces, exact
      zero area change, boundary 32→4, passed immediately. BUT running on
      a real remeshed component (dresser comp0001, comp0007) surfaced a
      genuine bug the synthetic test couldn't: `cost_map` has an entry for
      EVERY edge (protected ones included, at cost=inf), so filtering
      candidate loop-START edges by "in cost_map" alone let a
      hard-protected (boundary/crease) edge become a loop start and get
      dissolved — fixed by explicitly excluding `protected_set` when
      building candidates, plus a defense-in-depth check inside
      `trace_full_transverse_loop` itself. Also discovered or non-planar
      merged n-gons (any real curved component, confirmed on comp0001 — a
      tube bent into a rectangle), "total area" has NO single correct
      value: bmesh's own `calc_area()` and a from-scratch triangulated sum
      disagreed by 30%+ on the SAME final mesh, while both the boundary-
      edge-count invariant AND a trimesh watertight/winding-consistency
      check on the actual exported OBJ stayed clean throughout, and a
      before/after render was visually identical in silhouette. Redesigned
      the safety net accordingly: boundary-edge-count-never-increases is
      the one hard, planarity-independent gate; area drift is now an
      informational stat only (an absurd >500% swing still hard-fails, to
      catch a true catastrophic bug, not normal non-planar noise).
      Final verified result on comp0001: 6102→2934 faces, watertight=True,
      winding_consistent=True, silhouette visually unchanged.
- [x] **T8 — Darts & caps** (2026-11-01): `core/darts.py` (bmesh
      `join_triangles` at the COPLANAR_DART_DEG=24° threshold, boundary-
      edge-count checked unchanged) — tested on the dissolved comp0001:
      30 triangle pairs merged, quad% 74.96%→79.55%, boundary stayed 0.
      `core/caps.py` (bevel-ring + parallel-chord quad cap construction,
      ported from `burger_stand_retopo.py`) — found and fixed a real bug
      via self-test: bmesh leaves new edges' `.index` at -1 until an
      explicit renumbering, so keying a visited-set by `.index` silently
      collapsed every edge onto the same key and broke the loop walk after
      one step; fixed by keying on the edge object itself. After the fix,
      self-test (synthetic 16-gon open-top/open-bottom tube) produced
      EXACTLY the reference formula's numbers: 16 bevel quads + 7 chord
      quads = 23 pure quads per cap, 0 triangles, matching
      `structured_adaptive_retopo_report.md`'s own N_theta=16 example
      precisely.
- [x] **T9 — Reprojection** (2026-11-01): `core/reproject.py` — Blender
      SHRINKWRAP modifier snapping the simplified mesh onto the original
      dense component. Tested comp0001 (darted output) against its own
      original dense source: max vertex shift 0.0040 units = 0.43% of
      bbox diagonal, mean shift 0.012% — small corrective snap, not a
      distortion. Re-confirmed watertight=True, winding_consistent=True
      after reprojection (trimesh).
- [x] **T10 — Audit** (2026-11-01): `core/audit.py` ported faithfully
      (same formulas, reusing `io_blender` helpers instead of a separate
      embedded script). Verified against tripo_smart_engine's own
      `outputs/sofa_smart_quads.fbx` and the README's documented numbers
      for it: boundary_edges 61, valence_4_pct 90.66%, triangles_paired_pct
      23.31%, aspect median/90th/max 1.20/2.09/4.34 — EXACT match on every
      field.
- [x] **T11 — Pipeline orchestration** (2026-11-01, two more real bugs
      found and fixed via the first full end-to-end run): `core/pipeline.py`
      + `core/finalize_component.py` + `core/join_components.py`. First
      full run on the dresser FBX hit 5/36 components failing at the
      finalize stage with two distinct crashes:
      1. `dissolve.py`: "found the same (BMEdge) used multiple times" —
         a traced loop can revisit the same edge where its forward/backward
         walks meet, and `bmesh.ops.dissolve_edges` rejects a duplicate
         edge in its input outright. Fixed by deduping `edges_to_dissolve`
         via a set before the call.
      2. `protect.py`: "Vector.angle(other): zero length vectors have no
         valid angle" — the dome/saddle rule's `avg_n` (sum of surrounding
         face normals) can be near-zero at a genuine sharp fold where
         normals nearly cancel; `.angle()` on a zero vector raises. Fixed
         by detecting this and conservatively hard-protecting that vertex
         instead of crashing.
      Also made `finalize_component.py` fault-isolate each stage
      (dissolve/darts/caps/reproject) independently — one stage failing no
      longer discards the others' completed work, per the safe-degradation
      principle already established in remesh.py. Re-run after both fixes:
      0/36 finalize failures (down from 5/36), final asset 7,184 faces,
      67.94% quads, watertight join across 44 islands.
      **Known, documented limitation** (see TECH_NOTES): this input is
      already Tripo's OWN clean low-poly reference mesh (not a dense raw
      scan), so re-processing it is an out-of-scope stress test, not the
      intended use case — its quad%/valence-4% (67.94%/50.2%) are
      currently BELOW the original reference's own numbers for this exact
      asset (81.6%/85.6%), and `aspect_max` shows a 4882:1 outlier sliver
      not yet root-caused. T12 must validate against genuinely dense/raw
      inputs instead, where curvature-adaptive sizing actually applies.
- [x] **T12 — Full verification pass** (2026-11-01, on jade_sword.glb — a
      genuinely dense, non-Tripo-reference asset, per the important
      "dense input, not Tripo's own output" correction above): full
      pipeline run, 0/107 remesh failures, 0/107 finalize failures.
      Final: 8166 input faces → 1849 output faces (quad/tri/ngon mixed,
      64.41% quads). **Visual confirmation (`jade_final_render.png`) shows
      exactly the targeted curvature-adaptive result**: the flat blade
      collapsed to a handful of large clean faces (near-zero curvature →
      minimal faces), while the ornate hilt/guard retained dense detailed
      geometry (high curvature → preserved density) — this is the Primary
      Objective's exact target behavior, visually matching the curvature
      field measured back in T2 on this same asset.
      **Known residual issues, honestly documented, not yet fixed**:
      - A small visible notch/gap near the blade tip (minor local artifact,
        likely a dissolve/boundary interaction at a sliver component).
      - `boundary_edges` (1988) exceeds `faces` (1849) — far more open
        boundary than tripo_smart_engine's own jade sword reference (41
        boundary tears on a 24k-tri input, a different/larger source file
        than this session's 8k-face `assets/inputs/jade_sword.glb`, so not
        a strictly apples-to-apples number, but still a real fragmentation
        gap worth closing in a follow-up pass).
      - `valence_4_pct` (39.7%) is well below real Tripo references
        (64-92% range measured earlier) — the "flowed-ness" signature
        isn't yet at Tripo's level despite the correct curvature-adaptive
        shape emerging.
      These are legitimate next-iteration targets, not blockers: the
      core thesis (curvature-driven density, preserved detail, collapsed
      flats) is proven working end-to-end on real geometry.

## Additional real-world test: `002.glb` (500k tris, spider/scorpion-like creature)

Run 2026-11-01, user-requested. Robustness was excellent: 5/5 components
succeeded via quadriflow (no Instant Meshes or passthrough fallback
needed at all — the cleanest backend run of any asset tested), 0 remesh/
finalize failures, 500k→15,571 faces, only 18 boundary edges, 64.69%
quads, 86.3% of quads under 2:1 aspect ratio. **But the visual render
(`002_final_render.png`) exposed a real, previously-unseen quality gap**:
the body simplified reasonably, but the thin leg/appendage components are
covered in dense, chaotic triangle fans, not the flowing anisotropic quad
strips the engine targets — a sharp contrast to the jade sword's genuinely
clean blade collapse. Working hypothesis (not yet investigated): organic,
irregularly-bending thin limbs likely trigger much more crease/dome-
saddle hard-protection along their length than the jade sword's simpler,
more uniform blade and the dresser's straight tube-rail component, leaving
`dissolve.py` far less room to collapse them — this is the clearest
concrete lead for the next round of work on `protect.py`'s thresholds or
`dissolve.py`'s loop-tracing tolerance for organic/irregular thin parts.
This is reported honestly as a known gap, not claimed as solved — metrics
alone (which all looked fine here) are not sufficient proof of quality,
exactly per this session's own "render before moving on" rule.
