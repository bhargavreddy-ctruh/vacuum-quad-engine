# vacuum_quad_engine

A curvature-adaptive, quad-dominant retopology pipeline for turning dense
AI-generated (or any dense raw scan) meshes into clean, Tripo-style
quad-dominant assets: dense faces where curvature/detail genuinely exists,
large clean flat faces where it doesn't, with no fixed face-count budget.

See [`TECH_NOTES.md`](TECH_NOTES.md) for the full technical log (every
tool/library/threshold decision, every bug found and fixed, with evidence)
and [`PROGRESS.md`](PROGRESS.md) for the task-by-task build history.

## Pipeline stages (`core/`)

1. **`decompose.py`** — split the input mesh into connected components
   (never joined into one, unlike most naive retopology pipelines).
2. **`curvature.py`** — per-vertex curvature field (libigl), the single
   source of truth driving both sizing and protection downstream.
3. **`sizing.py`** — per-component, curvature-integrated target-face
   *hint* (never a hard budget) via an area-weighted integral of
   `h(v) = clip(sqrt(epsilon / curvature(v)), h_min, h_max)`.
4. **`remesh.py`** — field-aligned remeshing (Instant Meshes, falling back
   to `bin/quadriflow`) per component, with a real fragmentation guard
   (rejects a backend's output if it silently shatters a solid component
   into shrapnel) and a safe passthrough fallback if both backends fail.
5. **`protect.py`** — continuous, curvature-weighted edge protection
   (boundary / crease / dome-saddle hard gates; a smooth, locally-scaled
   micro-feature cost for everything else).
6. **`dissolve.py`** — transverse-loop and straight-slat dissolution,
   driven by the continuous cost field, lowest-cost (flattest) first.
7. **`darts.py`** / **`caps.py`** — coplanar triangle-pair merging and
   parallel-chord quad caps for planar circular/polygonal boundaries.
8. **`reproject.py`** — CAD-surface shrinkwrap back onto the original
   dense geometry.
9. **`audit.py`** — forensic topology metrics (quad%, valence-4%,
   boundary edges, aspect ratios), validated against known reference
   numbers.
10. **`pipeline.py`** — orchestrates all of the above end to end.

## Requirements

- Blender 5.x with `bpy` CLI access (`blender --background --python ...`)
- Python 3 with `numpy`, `trimesh`, `libigl` (`pip install numpy trimesh
  libigl`)
- A field-aligned remesher: Instant Meshes (preferred) and/or the bundled
  `bin/quadriflow` (built for macOS arm64 — rebuild from source for other
  platforms)

Edit `core/config.py` to point at your own binary paths if they differ
from the defaults.

## Usage

```bash
python3 core/pipeline.py <input_mesh.glb|.fbx|.obj> <output_dir>
```

Produces a per-component manifest, remeshed/finalized components, a
rejoined final asset (`<name>__final.obj`), and a JSON report with timing,
backend usage, and audit stats.

## Status

This is an active research/development pipeline, not a finished product.
See `PROGRESS.md` for what's verified and what's still a known gap
(current honest benchmark: quad% is close to real Tripo exports, but
flow regularity (valence-4%) is meaningfully below Tripo's own output —
see `benchmarks/tripo_reference_average.json` for the reference numbers
this is measured against).
