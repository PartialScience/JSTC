"""
SPICE netlist export of the coupled system.

Emits a subcircuit whose AC/transient behavior reproduces the coupled
model, so a designer can drop the real coil into a larger SPICE schematic
(driver, gap, strike load, ...).

Network topology:

  * Secondary: the transmission-line ladder. Node k (k = 1..N) carries the
    nodal voltage V_k; the reduced nodal capacitance matrix C becomes a
    capacitor network - a shunt capacitor to ground per node plus an
    inter-node capacitor per off-diagonal. The tent-basis C has POSITIVE
    adjacent off-diagonals, which become negative inter-node capacitors;
    SPICE accepts negative C and it is exact for AC. Segment inductors L_k
    connect the ladder nodes in series (base node grounded).
  * Coupling: the segment inductors and the primary inductor are magnetic
    (K-coupled) via the coupling coefficients derived from the bordered
    inductance matrix.
  * Primary: primary inductor L_p in series with the tank capacitor C_p,
    exposed at the port nodes.

This module builds the netlist as text and (for testing) can reconstruct
the defining matrices back from that text, so the export is verified for
self-consistency without running a SPICE engine.
"""
from __future__ import annotations

import numpy as np

from .coupled_system import CoupledSystem


def _fmt(x: float) -> str:
    """SPICE-friendly number (no unit suffixes, full precision)."""
    return f"{x:.12g}"


def export_spice_subcircuit(sys: CoupledSystem, name: str = "teslacoil") -> str:
    """Build a SPICE subcircuit for the coupled system.

    The subcircuit exposes two port nodes (the primary tank terminals):

        .subckt <name> prim_in prim_gnd

    Args:
        sys: The coupled system (SI units).
        name: Subcircuit name.

    Returns:
        The netlist text.
    """
    n = sys.order
    C = sys.capacitance
    L = sys.inductance
    m = sys.coupling
    Lp = sys.primary_inductance
    Cp = sys.tank_capacitance

    lines: list[str] = []
    lines.append(f"* Coupled Tesla coil, N={n} secondary segments")
    lines.append(f".subckt {name} prim_in prim_gnd")

    # --- Secondary capacitance network (nodes s1..sN, base = ground '0') ---
    # Shunt (to-ground) capacitance at node k = row sum of C (so that the
    # capacitor network's nodal matrix equals C exactly: diagonal = sum of
    # incident caps, off-diagonal = -inter-node cap).
    for i in range(n):
        shunt = float(np.sum(C[i]))
        lines.append(f"Csh{i+1} s{i+1} 0 {_fmt(shunt)}")
    for i in range(n):
        for j in range(i + 1, n):
            c_ij = float(C[i, j])
            if c_ij != 0.0:
                # nodal off-diagonal C_ij = -(inter-node cap) => cap = -C_ij
                lines.append(f"Cm{i+1}_{j+1} s{i+1} s{j+1} {_fmt(-c_ij)}")

    # --- Secondary segment inductors (series ladder, base node grounded) ---
    # Segment k connects node k to node k-1 (node 0 = ground). Series
    # connectivity A is upper-bidiagonal (diag 1, super-diag -1).
    for k in range(n):
        lo = "0" if k == 0 else f"s{k}"
        lines.append(f"Lseg{k+1} s{k+1} {lo} {_fmt(float(L[k, k]))}")

    # --- Primary: inductor in series with tank cap between the ports ---
    lines.append(f"Lprim prim_in pmid {_fmt(Lp)}")
    lines.append(f"Ctank pmid prim_gnd {_fmt(Cp)}")

    # --- Magnetic coupling (K statements) from the bordered inductance ---
    # k_ij = M_ij / sqrt(L_ii L_jj). Segment-segment from L off-diagonals,
    # segment-primary from the coupling vector m.
    def kstmt(tag, la, lb, mutual, self_a, self_b):
        coeff = mutual / np.sqrt(self_a * self_b)
        return f"K{tag} {la} {lb} {_fmt(float(coeff))}"

    for i in range(n):
        for j in range(i + 1, n):
            if L[i, j] != 0.0:
                lines.append(kstmt(f"s{i+1}_s{j+1}", f"Lseg{i+1}", f"Lseg{j+1}",
                                   L[i, j], L[i, i], L[j, j]))
    for i in range(n):
        if m[i] != 0.0:
            lines.append(kstmt(f"s{i+1}_p", f"Lseg{i+1}", "Lprim",
                               m[i], L[i, i], Lp))

    lines.append(f".ends {name}")
    return "\n".join(lines) + "\n"


def reconstruct_from_spice(netlist: str) -> CoupledSystem:
    """Rebuild the CoupledSystem from an exported netlist.

    Used to verify the export is self-consistent (round-trip): parsing the
    text back must reproduce the original matrices. Not a general SPICE
    parser - it understands only the elements this module emits.
    """
    caps_shunt: dict[int, float] = {}
    caps_inter: dict[tuple[int, int], float] = {}
    seg_L: dict[int, float] = {}
    Lp = None
    Cp = None
    k_seg: dict[tuple[int, int], float] = {}
    k_prim: dict[int, float] = {}

    def node_idx(tok: str) -> int:
        return 0 if tok == "0" else int(tok[1:])

    for raw in netlist.splitlines():
        line = raw.strip()
        if not line or line.startswith("*") or line.startswith("."):
            continue
        parts = line.split()
        ref = parts[0]
        if ref.startswith("Csh"):
            caps_shunt[int(ref[3:])] = float(parts[3])
        elif ref.startswith("Cm"):
            i, j = (int(x) for x in ref[2:].split("_"))
            caps_inter[(i, j)] = float(parts[3])
        elif ref.startswith("Lseg"):
            seg_L[int(ref[4:])] = float(parts[3])
        elif ref == "Lprim":
            Lp = float(parts[3])
        elif ref == "Ctank":
            Cp = float(parts[3])
        elif ref.startswith("Ks") and "_p" in ref:
            i = int(ref[2:].split("_")[0])
            k_prim[i] = float(parts[3])
        elif ref.startswith("Ks"):
            a, b = ref[2:].split("_")
            k_seg[(int(a[1:]) if a.startswith("s") else int(a),
                   int(b[1:]) if b.startswith("s") else int(b))] = float(parts[3])

    n = len(seg_L)
    L = np.zeros((n, n))
    for k in range(1, n + 1):
        L[k - 1, k - 1] = seg_L[k]
    C = np.zeros((n, n))
    for (i, j), c in caps_inter.items():
        C[i - 1, j - 1] = -c
        C[j - 1, i - 1] = -c
    for i in range(1, n + 1):
        # diagonal = shunt + sum of incident inter-node caps
        row_off = sum(-C[i - 1, j] for j in range(n) if j != i - 1)
        C[i - 1, i - 1] = caps_shunt[i] + row_off

    m = np.zeros(n)
    for i, coeff in k_prim.items():
        m[i - 1] = coeff * np.sqrt(L[i - 1, i - 1] * Lp)
    for (a, b), coeff in k_seg.items():
        val = coeff * np.sqrt(L[a - 1, a - 1] * L[b - 1, b - 1])
        L[a - 1, b - 1] = val
        L[b - 1, a - 1] = val

    A = np.eye(n) + np.diag([-1.0] * (n - 1), k=1)
    return CoupledSystem(
        capacitance=C, inductance=L, connectivity=A, coupling=m,
        primary_inductance=Lp, tank_capacitance=Cp,
    )
