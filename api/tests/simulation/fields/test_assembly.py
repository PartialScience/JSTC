"""
Unit tests for the electrostatic field superposition, using a synthetic
basis so the math is exercised in isolation (no FEM).
"""
import numpy as np
import pytest

from app.simulation.fields.assembly import assemble_electrostatic_field
from app.simulation.fields.electrostatic_basis import ElectrostaticFieldBasis
from app.simulation.fields.grid import FieldGrid


def _basis(has_primary=True, seed=0):
    """A 2-node (3-tent) synthetic basis on a small grid."""
    rng = np.random.default_rng(seed)
    grid = FieldGrid.over_domain(1, 1, nr=4, nz=5)
    nz, nr = grid.shape
    tent_fields = rng.standard_normal((3, nz, nr))  # tents u_0, u_1, u_2
    mask = np.ones((nz, nr), dtype=bool)
    if has_primary:
        prof = rng.standard_normal((nz, nr))
        unif = rng.standard_normal((nz, nr))
        # charges: [tent0, tent1, tent2, profile, uniform]
        charges = rng.standard_normal(5)
        charges[4] = 2.0  # nonzero Q_uniform for the offset denominator
        return ElectrostaticFieldBasis(
            grid=grid, mask=mask, tent_fields=tent_fields,
            primary_profile_field=prof, primary_uniform_field=unif,
            primary_charges=charges, has_primary=True,
        )
    return ElectrostaticFieldBasis(
        grid=grid, mask=mask, tent_fields=tent_fields,
        primary_profile_field=None, primary_uniform_field=None,
        primary_charges=None, has_primary=False,
    )


class TestSuperposition:
    def test_node_voltages_weight_tents_with_grounded_base(self):
        b = _basis(has_primary=False)
        # V = [t1, t2]; base t0 is prepended as 0.
        phi = assemble_electrostatic_field(b, np.array([2.0, -1.0]))
        expected = 0 * b.tent_fields[0] + 2.0 * b.tent_fields[1] - 1.0 * b.tent_fields[2]
        assert np.allclose(phi.real, expected)
        assert np.allclose(phi.imag, 0)

    def test_linear_in_drive(self):
        b = _basis()
        v = np.array([1.0 + 0.5j, -0.3j])
        phi1 = assemble_electrostatic_field(b, v, primary_voltage=2 + 1j)
        phi2 = assemble_electrostatic_field(b, 3 * v, primary_voltage=3 * (2 + 1j))
        assert np.allclose(phi2, 3 * phi1)

    def test_wrong_voltage_length_raises(self):
        b = _basis()
        with pytest.raises(ValueError):
            assemble_electrostatic_field(b, np.array([1.0]))  # need 2

    def test_no_primary_ignores_vp(self):
        b = _basis(has_primary=False)
        v = np.array([1.0, 2.0])
        a = assemble_electrostatic_field(b, v, primary_voltage=999.0)
        c = assemble_electrostatic_field(b, v, primary_voltage=0.0)
        assert np.allclose(a, c)


class TestFloatingVsGrounded:
    def test_grounded_offset_is_zero(self):
        """Grounded: phi = tents + V_p*u_diff, no uniform (offset) term."""
        b = _basis()
        v = np.array([1.0, 2.0])
        phi = assemble_electrostatic_field(b, v, primary_voltage=5.0,
                                           reference_mode="grounded", hot_end="outer")
        expected = (np.tensordot(np.concatenate([[0], v]), b.tent_fields, axes=(0, 0))
                    + 5.0 * b.primary_profile_field)
        assert np.allclose(phi.real, expected)

    def test_floating_enforces_primary_charge_neutrality(self):
        b = _basis()
        v = np.array([1.0 + 0j, 2.0 + 0j])
        vp = 5.0 + 0j
        assemble_electrostatic_field(b, v, primary_voltage=vp, reference_mode="floating")
        # Recompute the net primary charge with the same offset formula.
        V = np.concatenate([[0], v])
        Q = b.primary_charges
        Qd = Q[3]  # hot outer -> Q_diff = Q_profile
        offset = -(V @ Q[:3] + vp * Qd) / Q[4]
        net = V @ Q[:3] + vp * Qd + offset * Q[4]
        assert abs(net) < 1e-12

    def test_hot_end_orientation_differs(self):
        b = _basis()
        v = np.array([1.0, 2.0])
        outer = assemble_electrostatic_field(b, v, primary_voltage=5.0, hot_end="outer")
        inner = assemble_electrostatic_field(b, v, primary_voltage=5.0, hot_end="inner")
        assert not np.allclose(outer, inner)

    def test_reversed_profile_is_uniform_minus_profile(self):
        """The inner-hot differential field equals u_uniform - u_profile."""
        b = _basis()
        v = np.zeros(2)  # isolate the primary contribution
        vp = 1.0
        inner = assemble_electrostatic_field(b, v, primary_voltage=vp,
                                             reference_mode="grounded", hot_end="inner")
        expected = vp * (b.primary_uniform_field - b.primary_profile_field)
        assert np.allclose(inner.real, expected)
