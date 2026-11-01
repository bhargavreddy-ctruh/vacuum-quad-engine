"""Per-component finishing: dissolve -> darts -> caps -> reproject, all in
ONE Blender process (avoids 4x import/export overhead per component).
Runs under Blender.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import bpy
import bmesh

import io_blender
import dissolve
import darts
import caps
import reproject


def finalize(remeshed_obj, original_dense_obj, out_obj, max_passes=20):
    """Each stage is independently fault-isolated: a failure in dissolve,
    darts, or caps rolls that one stage back (re-reads the mesh as it stood
    before that stage) and continues with the rest, rather than discarding
    all prior work for the component. Safe degradation over total failure,
    per the Primary objective — a component that only gets dissolve+darts
    (caps failing) is still a correct, useful result.
    """
    io_blender.clear_scene()
    objs = io_blender.import_mesh(remeshed_obj)
    obj = objs[0]
    bm = bmesh.new()
    bm.from_mesh(obj.data)

    stage_errors = {}

    dissolve_stats = None
    try:
        dissolve_stats = dissolve.simplify_component(bm, max_passes=max_passes)
    except Exception as e:
        stage_errors["dissolve"] = str(e)
        bm.free()
        bm = bmesh.new()
        bm.from_mesh(obj.data)

    darts_stats = None
    try:
        darts_stats = darts.merge_coplanar_triangle_pairs(bm)
    except Exception as e:
        stage_errors["darts"] = str(e)

    caps_results = None
    try:
        bm.edges.ensure_lookup_table()
        caps_results = caps.cap_all_planar_boundaries(bm)
    except Exception as e:
        stage_errors["caps"] = str(e)

    bm.to_mesh(obj.data)
    obj.data.update()
    bm.free()

    tmp_path = out_obj + ".pre_reproject.obj"
    io_blender.export_mesh(tmp_path, objects=[obj], quads=True)

    reproject_stats = None
    try:
        reproject_stats = reproject.reproject_obj_files(tmp_path, original_dense_obj, out_obj)
    except Exception as e:
        stage_errors["reproject"] = str(e)
        # Reprojection failing just means ship the pre-reprojection geometry
        # unchanged rather than losing the component entirely.
        os.replace(tmp_path, out_obj)
    else:
        try:
            os.remove(tmp_path)
        except OSError:
            pass

    return {
        "dissolve": dissolve_stats,
        "darts": darts_stats,
        "caps": caps_results,
        "reproject": reproject_stats,
        "stage_errors": stage_errors,
        "out_obj": out_obj,
    }


if __name__ == "__main__":
    argv = sys.argv
    args = argv[argv.index("--") + 1:] if "--" in argv else argv[1:]
    if len(args) < 3:
        print("Usage: blender --background --python finalize_component.py -- <remeshed.obj> <original_dense.obj> <out.obj>")
        sys.exit(1)
    try:
        result = finalize(args[0], args[1], args[2])
        result["ok"] = True
    except Exception as e:
        result = {"ok": False, "error": str(e), "out_obj": args[2]}
    print("FINALIZE_RESULT_JSON_START")
    print(json.dumps(result, indent=2))
    print("FINALIZE_RESULT_JSON_END")
