"""
General-purpose converter from Gmsh mesh data to a PyMFEM mesh object.

Supports:
  - 1D, 2D, and 3D meshes
  - Triangles, quads, tetrahedra, hexahedra, wedges/prisms, pyramids
  - Mixed element meshes (e.g. tets + pyramids + hexes)
  - Higher-order Gmsh meshes (automatically reduced to first-order)
  - Physical group tags preserved as MFEM element/boundary attributes
  - 2D meshes embedded in 3D space (non-zero z coordinates)
  - Auto-detection of mesh and space dimensions
"""
from __future__ import annotations

import numpy as np
import mfem.ser as mfem


# ---------------------------------------------------------------------------
# Gmsh element type catalogue
# Maps gmsh_type -> (dim, num_primary_nodes, base_type)
# base_type groups higher-order variants with their first-order parent.
# num_primary_nodes is the number of corner (first-order) nodes.
# ---------------------------------------------------------------------------
_GMSH_ELEM = {
    # First-order
    15: (0, 1,  "point"),
    1:  (1, 2,  "line"),
    2:  (2, 3,  "triangle"),
    3:  (2, 4,  "quad"),
    4:  (3, 4,  "tet"),
    5:  (3, 8,  "hex"),
    6:  (3, 6,  "wedge"),
    7:  (3, 5,  "pyramid"),
    # Second-order
    8:  (1, 2,  "line"),
    9:  (2, 3,  "triangle"),
    10: (2, 4,  "quad"),
    11: (3, 4,  "tet"),
    12: (3, 8,  "hex"),
    13: (3, 6,  "wedge"),
    14: (3, 5,  "pyramid"),
    16: (2, 4,  "quad"),       # 8-node serendipity quad
    17: (3, 8,  "hex"),        # 20-node serendipity hex
    18: (3, 6,  "wedge"),      # 15-node 2nd-order wedge
    19: (3, 5,  "pyramid"),    # 13-node 2nd-order pyramid
}
# Add higher-order lines (order 3-10, types 26-28, 62-66)
for _t in [26, 27, 28, 62, 63, 64, 65, 66]:
    _GMSH_ELEM[_t] = (1, 2, "line")
# Higher-order triangles (orders 3-10)
for _t in [20, 21, 22, 23, 24, 25, 42, 43, 44, 45, 46, 52, 53, 54, 55, 56]:
    _GMSH_ELEM[_t] = (2, 3, "triangle")
# Higher-order quads (orders 3-10)
for _t in [36, 37, 38, 39, 40, 41, 47, 48, 49, 50, 51, 57, 58, 59, 60, 61]:
    _GMSH_ELEM[_t] = (2, 4, "quad")
# Higher-order tets (orders 3-10)
for _t in [29, 30, 31, 32, 33, 71, 72, 73, 74, 75, 79, 80, 81, 82, 83]:
    _GMSH_ELEM[_t] = (3, 4, "tet")
# Higher-order hexes (orders 3-9)
for _t in [92, 93, 94, 95, 96, 97, 98, 99]:
    _GMSH_ELEM[_t] = (3, 8, "hex")

# MFEM element-adding functions keyed by base_type.
# Each takes (mesh, vertex_indices, attribute).
_ADD_VOLUME = {
    "line":     lambda m, v, a: m.AddSegment(v[0], v[1], a),
    "triangle": lambda m, v, a: m.AddTriangle(v[0], v[1], v[2], a),
    "quad":     lambda m, v, a: m.AddQuad(v[0], v[1], v[2], v[3], a),
    "tet":      lambda m, v, a: m.AddTet(v[0], v[1], v[2], v[3], a),
    "hex":      lambda m, v, a: m.AddHex(v[0], v[1], v[2], v[3],
                                         v[4], v[5], v[6], v[7], a),
    "wedge":    lambda m, v, a: m.AddWedge(v[0], v[1], v[2],
                                           v[3], v[4], v[5], a),
    "pyramid":  lambda m, v, a: m.AddPyramid(v[0], v[1], v[2],
                                             v[3], v[4], a),
}
_ADD_BDR = {
    "point":    lambda m, v, a: m.AddBdrPoint(v[0], a),
    "line":     lambda m, v, a: m.AddBdrSegment(v[0], v[1], a),
    "triangle": lambda m, v, a: m.AddBdrTriangle(v[0], v[1], v[2], a),
    "quad":     lambda m, v, a: m.AddBdrQuad(v[0], v[1], v[2], v[3], a),
}


def extract_gmsh_data(gmsh_module) -> dict:
    """
    Extract all mesh data needed for conversion from an active Gmsh model.

    Call this after gmsh.model.mesh.generate() and before gmsh.finalize().
    This pulls data out of the Gmsh singleton so that the pure converter
    function ``gmsh_to_mfem`` can work without touching Gmsh state.

    Args:
        gmsh_module: The ``gmsh`` module (i.e. ``import gmsh; ... gmsh``).

    Returns:
        A dict suitable for unpacking into ``gmsh_to_mfem(**data)``.
    """
    gm = gmsh_module
    node_tags, node_coords, _ = gm.model.mesh.getNodes()
    elem_types, _, elem_node_tags = gm.model.mesh.getElements()

    # Build element_tag -> physical_group_tag mapping
    elem_tag_to_phys: dict[int, int] = {}
    for dim, phys_tag in gm.model.getPhysicalGroups():
        for entity_tag in gm.model.getEntitiesForPhysicalGroup(dim, phys_tag):
            etypes, etags, _ = gm.model.mesh.getElements(dim, entity_tag)
            for tag_arr in etags:
                for et in tag_arr:
                    # First physical group wins; don't overwrite
                    elem_tag_to_phys.setdefault(int(et), phys_tag)

    # Rebuild elem_tags so the converter can look up attributes
    _, elem_tags, _ = gm.model.mesh.getElements()

    return dict(
        node_tags=node_tags,
        node_coords=node_coords,
        elem_types=elem_types,
        elem_node_tags=elem_node_tags,
        elem_tags=elem_tags,
        elem_tag_to_phys=elem_tag_to_phys,
    )


def gmsh_to_mfem(
    node_tags: np.ndarray,
    node_coords: np.ndarray,
    elem_types: np.ndarray,
    elem_node_tags: list[np.ndarray],
    elem_tags: list[np.ndarray] | None = None,
    elem_tag_to_phys: dict[int, int] | None = None,
) -> mfem.Mesh:
    """
    Convert Gmsh mesh arrays into an mfem.Mesh object entirely in memory.

    Args:
        node_tags:       1D array of integer node tags from
                         ``gmsh.model.mesh.getNodes()``.
        node_coords:     1D float array of coordinates (x0,y0,z0, x1,y1,z1, ...)
                         from ``gmsh.model.mesh.getNodes()``.
        elem_types:      1D array of Gmsh element-type codes from
                         ``gmsh.model.mesh.getElements()``.
        elem_node_tags:  List of 1D arrays, one per element type, each holding
                         concatenated node tags for those elements.
        elem_tags:       (Optional) List of 1D arrays, one per element type,
                         each holding Gmsh element tags. Used together with
                         *elem_tag_to_phys* to assign MFEM attributes.
        elem_tag_to_phys: (Optional) Dict mapping Gmsh element tag -> physical
                         group tag. Use ``extract_gmsh_data`` to build this
                         easily. When provided, physical group tags become
                         MFEM element/boundary attributes. When absent, all
                         attributes default to 1.

    Returns:
        A fully constructed ``mfem.Mesh``.

    Raises:
        ValueError: On unsupported element types, empty meshes, or other
                    inconsistencies.
    """
    # ---- Validate inputs ----
    if len(node_tags) == 0:
        raise ValueError("No nodes in the mesh.")
    if len(elem_types) == 0:
        raise ValueError("No elements in the mesh.")
    if len(elem_types) != len(elem_node_tags):
        raise ValueError(
            f"elem_types length ({len(elem_types)}) != "
            f"elem_node_tags length ({len(elem_node_tags)})."
        )
    if elem_tags is not None and len(elem_tags) != len(elem_types):
        raise ValueError(
            f"elem_tags length ({len(elem_tags)}) != "
            f"elem_types length ({len(elem_types)})."
        )

    # ---- Remap node tags to contiguous 0-based indices ----
    tag_to_idx = {int(tag): i for i, tag in enumerate(node_tags)}
    coords = node_coords.reshape(-1, 3)
    num_verts = len(node_tags)

    # ---- Parse and classify elements by dimension ----
    # Each entry: (base_type, vertex_indices[N x primary_nodes], attributes[N])
    elems_by_dim: dict[int, list[tuple[str, np.ndarray, np.ndarray]]] = {}
    has_higher_order = False

    for i, etype in enumerate(elem_types):
        etype = int(etype)
        if etype not in _GMSH_ELEM:
            raise ValueError(
                f"Unsupported Gmsh element type {etype}. "
                "Only standard simplex/tensor-product elements are supported."
            )
        dim, num_primary, base_type = _GMSH_ELEM[etype]

        raw_nodes = elem_node_tags[i]
        if len(raw_nodes) == 0:
            continue

        # Determine total nodes per element from the data
        n_elems_for_type = (
            len(elem_tags[i]) if elem_tags is not None else None
        )
        if n_elems_for_type is not None and n_elems_for_type > 0:
            total_nodes_per = len(raw_nodes) // n_elems_for_type
        else:
            # Infer from the element type catalogue
            total_nodes_per = num_primary  # fallback for first-order
            # For higher-order, we need the actual count from Gmsh
            # Try common known total node counts
            for candidate in range(num_primary, 300):
                if len(raw_nodes) % candidate == 0:
                    total_nodes_per = candidate
                    break

        if total_nodes_per > num_primary:
            has_higher_order = True

        all_nodes = raw_nodes.reshape(-1, total_nodes_per)
        # Keep only primary (corner) nodes for first-order MFEM mesh
        primary = all_nodes[:, :num_primary]
        n_elems = len(primary)

        # Map node tags -> 0-based indices
        try:
            indices = np.array(
                [[tag_to_idx[int(n)] for n in row] for row in primary],
                dtype=np.int32,
            )
        except KeyError as exc:
            raise ValueError(
                f"Element references node tag {exc} which is not in node_tags."
            ) from exc

        # Build attribute array
        if elem_tags is not None and elem_tag_to_phys is not None:
            attrs = np.array(
                [elem_tag_to_phys.get(int(t), 1) for t in elem_tags[i]],
                dtype=np.int32,
            )
        else:
            attrs = np.ones(n_elems, dtype=np.int32)

        elems_by_dim.setdefault(dim, []).append((base_type, indices, attrs))

    if not elems_by_dim:
        raise ValueError("No recognisable elements found in the mesh data.")

    if has_higher_order:
        import warnings
        warnings.warn(
            "Higher-order Gmsh elements detected. Only corner (first-order) "
            "nodes are used. The resulting MFEM mesh is first-order. "
            "Use mfem.Mesh.SetCurvature() afterwards if you need curved "
            "elements.",
            stacklevel=2,
        )

    # ---- Determine mesh dimension and space dimension ----
    mesh_dim = max(elems_by_dim.keys())
    bdr_dim = mesh_dim - 1

    # Space dimension: use 3 if mesh is 3D, or if 2D mesh has non-zero z
    if mesh_dim == 3:
        space_dim = 3
    elif mesh_dim == 2:
        z_coords = coords[:, 2]
        space_dim = 3 if np.any(np.abs(z_coords) > 1e-15) else 2
    else:
        space_dim = 1

    # ---- Gather volume and boundary element lists ----
    volume_groups = elems_by_dim.get(mesh_dim, [])
    bdr_groups = elems_by_dim.get(bdr_dim, [])

    num_elems = sum(len(idx) for _, idx, _ in volume_groups)
    num_bdr = sum(len(idx) for _, idx, _ in bdr_groups)

    if num_elems == 0:
        raise ValueError(
            f"No {mesh_dim}D volume elements found. "
            "Ensure the mesh has been generated at the correct dimension."
        )

    # ---- Build MFEM mesh ----
    mesh = mfem.Mesh(mesh_dim, num_verts, num_elems, num_bdr, space_dim)

    # Add vertices
    for i in range(num_verts):
        mesh.AddVertex(coords[i, 0], coords[i, 1], coords[i, 2])

    # Add volume elements
    for base_type, indices, attrs in volume_groups:
        add_fn = _ADD_VOLUME.get(base_type)
        if add_fn is None:
            raise ValueError(f"No MFEM volume element for type '{base_type}'.")
        for row, attr in zip(indices, attrs):
            add_fn(mesh, row.tolist(), int(attr))

    # Add boundary elements
    for base_type, indices, attrs in bdr_groups:
        add_fn = _ADD_BDR.get(base_type)
        if add_fn is None:
            raise ValueError(
                f"No MFEM boundary element for type '{base_type}'."
            )
        for row, attr in zip(indices, attrs):
            add_fn(mesh, row.tolist(), int(attr))

    mesh.FinalizeMesh()
    return mesh
