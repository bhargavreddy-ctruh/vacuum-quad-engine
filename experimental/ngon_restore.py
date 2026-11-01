"""N-gon restoration: triangulate any face with >4 vertices, then immediately
re-pair triangles into quads via join_triangles. This is the missing step
ribbon_engine.py always runs after dissolution ("0% N-GON RESTORATION") that
our dissolve.py never ported — without it, a dissolve pass that merges many
quads can leave a sprawling n-gon (seen: up to a 22-gon) that never gets
cleaned back into quads, degrading the "clean structured quads" goal.

Standalone/experimental on purpose (per user's "proceed with caution, don't
touch the existing pipeline" instruction) — tested in isolation here first.
"""
import json
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "core"))

import bpy
import bmesh

import io_blender
import config


def restore_ngons_to_quads(bm, angle_face_deg=config.COPLANAR_DART_DEG, angle_shape_deg=90.0):
    bm.faces.ensure_lookup_table()
    ngons = [f for f in bm.faces if len(f.verts) > 4]
    n_ngons_before = len(ngons)
    if ngons:
        bmesh.ops.triangulate(bm, faces=ngons)

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    n_tris_before_join = sum(1 for f in bm.faces if len(f.verts) == 3)
    bmesh.ops.join_triangles(
        bm, faces=bm.faces,
        angle_face_threshold=math.radians(angle_face_deg),
        angle_shape_threshold=math.radians(angle_shape_deg),
    )
    bm.faces.ensure_lookup_table()
    n_tris_after_join = sum(1 for f in bm.faces if len(f.verts) == 3)
    n_ngons_after = sum(1 for f in bm.faces if len(f.verts) > 4)

    return {
        "ngons_before": n_ngons_before,
        "ngons_after": n_ngons_after,
        "tris_before_join": n_tris_before_join,
        "tris_after_join": n_tris_after_join,
    }


def process_obj(in_obj, out_obj):
    io_blender.clear_scene()
    objs = io_blender.import_mesh(in_obj)
    obj = objs[0]
    bm = bmesh.new()
    bm.from_mesh(obj.data)

    n_boundary_before = sum(1 for e in bm.edges if e.is_boundary)
    stats = restore_ngons_to_quads(bm)
    bm.edges.ensure_lookup_table()
    n_boundary_after = sum(1 for e in bm.edges if e.is_boundary)
    stats["boundary_before"] = n_boundary_before
    stats["boundary_after"] = n_boundary_after
    if n_boundary_after > n_boundary_before:
        raise RuntimeError(f"ngon_restore: boundary grew {n_boundary_before}->{n_boundary_after}")

    bm.to_mesh(obj.data)
    obj.data.update()
    bm.free()
    io_blender.export_mesh(out_obj, objects=[obj], quads=True)
    stats["out_obj"] = out_obj
    return stats


if __name__ == "__main__":
    argv = sys.argv
    args = argv[argv.index("--") + 1:] if "--" in argv else argv[1:]
    if len(args) < 2:
        print("Usage: blender --background --python ngon_restore.py -- <in.obj> <out.obj>")
        sys.exit(1)
    stats = process_obj(args[0], args[1])
    print("NGON_RESTORE_RESULT_JSON_START")
    print(json.dumps(stats, indent=2))
    print("NGON_RESTORE_RESULT_JSON_END")
