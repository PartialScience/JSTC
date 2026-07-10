"""
Tests for the magnetic A_phi basis and superposition. The loop kernel is
validated against the analytic on-axis field B_z(center) = mu0 I / (2a).
"""
import numpy as np
import pytest

from app.simulation.fields.grid import FieldGrid
from app.simulation.fields.magnetic_basis import (
    MU0,
    MagneticFieldBasis,
    assemble_magnetic_field,
    loop_vector_potential,
)


class TestLoopKernel:
    def test_center_field_matches_analytic(self):
        a = 1.0
        rs = np.array([0.02, 0.03, 0.04])
        z = np.zeros_like(rs)
        aphi = np.array(
            [loop_vector_potential(np.array([r]), np.array([zz]), a, 0.0)[0]
             for r, zz in zip(rs, z)]
        )
        # Near the axis A_phi ~ (B_z/2) r, so B_z = 2 A_phi / r.
        bz = 2 * aphi / rs
        assert np.allclose(bz, MU0 / (2 * a), rtol=2e-3)

    def test_zero_on_axis(self):
        val = loop_vector_potential(np.array([0.0]), np.array([0.5]), 1.0, 0.0)
        assert val[0] == 0.0

    def test_scale_invariance(self):
        """A_phi depends only on coordinate ratios: scaling loop and point
        together leaves it unchanged."""
        a1 = loop_vector_potential(np.array([2.0]), np.array([1.0]), 3.0, 0.0)[0]
        s = 10.0
        a2 = loop_vector_potential(np.array([2.0 * s]), np.array([1.0 * s]), 3.0 * s, 0.0)[0]
        assert a2 == pytest.approx(a1, rel=1e-9)


def _basis(n_seg=3, has_primary=True, seed=0):
    rng = np.random.default_rng(seed)
    grid = FieldGrid.over_domain(1, 1, nr=4, nz=5)
    nz, nr = grid.shape
    seg = rng.standard_normal((n_seg, nz, nr))
    prim = rng.standard_normal((nz, nr)) if has_primary else None
    return MagneticFieldBasis(grid=grid, seg_fields=seg, primary_field=prim,
                              has_primary=has_primary)


class TestAssembly:
    def test_superposes_segment_currents(self):
        b = _basis(has_primary=False)
        I = np.array([1.0, 2.0, -1.0])
        a = assemble_magnetic_field(b, I)
        expected = np.tensordot(I, b.seg_fields, axes=(0, 0))
        assert np.allclose(a.real, expected)

    def test_primary_current_adds_primary_field(self):
        b = _basis()
        I = np.zeros(3)
        a = assemble_magnetic_field(b, I, primary_current=4.0)
        assert np.allclose(a.real, 4.0 * b.primary_field)

    def test_linear_and_complex(self):
        b = _basis()
        I = np.array([1 + 1j, 0.5j, -2.0])
        a1 = assemble_magnetic_field(b, I, primary_current=1 + 0j)
        a2 = assemble_magnetic_field(b, 2 * I, primary_current=2 + 0j)
        assert np.allclose(a2, 2 * a1)

    def test_wrong_length_raises(self):
        with pytest.raises(ValueError):
            assemble_magnetic_field(_basis(n_seg=3), np.zeros(2))
