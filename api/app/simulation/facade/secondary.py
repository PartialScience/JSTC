from __future__ import annotations

from typing import TYPE_CHECKING, Tuple

import numpy as np
from scipy.constants import epsilon_0, mu_0

if TYPE_CHECKING:
    from app.simulation.facade.simulation import TeslaCoilSimulation


class SecondaryView:
    """Lazy computed properties pertaining to the secondary coil.

    Units policy: the solvers work in the coil's geometric units and this
    view applies physics exactly once -

        L [H] = mu_0 * unit_scale * L_geo
        C [F] = 2*pi*epsilon_0 * unit_scale * C_geo

    so every property below is in SI (Hz, H, F, Ohm, m) unless its name
    says otherwise.
    """

    #: Temperature used for material properties, matching JavaTC's
    #: 68 F ambient. TODO: make simulation ambient temperature a model input.
    _AMBIENT_K = 293.15

    def __init__(self, sim: TeslaCoilSimulation):
        self._sim = sim

    # -- Geometric matrices (solver-native units) -----------------------------

    @property
    def capacitance_matrix_geo(self) -> Tuple[Tuple[float, ...], ...]:
        """Grounded-reduced NxN nodal capacitance matrix, geometric units.

        Derived from the full nodal matrix by dropping the grounded base
        node t_0 (row/col 0), matching the series-connectivity convention.
        """
        nodal = self.nodal_capacitance_matrix_geo
        return tuple(row[1:] for row in nodal[1:])

    @property
    def nodal_capacitance_matrix_geo(self) -> Tuple[Tuple[float, ...], ...]:
        """Full (N+1)x(N+1) nodal capacitance matrix, geometric units."""
        return self._sim._matrices.nodal_capacitance_geo()

    @property
    def inductance_matrix_geo(self) -> Tuple[Tuple[float, ...], ...]:
        """NxN segment inductance matrix, geometric units."""
        return self._sim._matrices.inductance_geo()

    # -- SI matrices -----------------------------------------------------------

    @property
    def capacitance_matrix(self) -> Tuple[Tuple[float, ...], ...]:
        """Grounded-reduced nodal capacitance matrix C in Farads."""
        s = self._sim.coil.unit_scale
        C = np.array(self.capacitance_matrix_geo) * (2 * np.pi * epsilon_0 * s)
        return tuple(tuple(row) for row in C)

    @property
    def nodal_capacitance_matrix(self) -> Tuple[Tuple[float, ...], ...]:
        """Full nodal capacitance matrix (including the grounded base node)
        in Farads."""
        s = self._sim.coil.unit_scale
        C = np.array(self.nodal_capacitance_matrix_geo) * (2 * np.pi * epsilon_0 * s)
        return tuple(tuple(row) for row in C)

    @property
    def inductance_matrix(self) -> Tuple[Tuple[float, ...], ...]:
        """Segment mutual inductance matrix L in Henries."""
        s = self._sim.coil.unit_scale
        L = np.array(self.inductance_matrix_geo) * (mu_0 * s)
        return tuple(tuple(row) for row in L)

    @property
    def connectivity_matrix(self) -> Tuple[Tuple[float, ...], ...]:
        """Series connectivity matrix A (dimensionless)."""
        coil = self._sim.coil
        return self._sim._conn_solver.compute_connectivity_matrix(
            discretization_order=coil.discretization_order,
        )

    # -- Eigen analysis --------------------------------------------------------

    @property
    def eigen_frequencies(self) -> Tuple[float, ...]:
        """Eigenfrequencies in Hz, sorted ascending."""
        return self._sim._eigen_solver.compute_eigen_frequencies(
            capacitance_matrix=self.capacitance_matrix,
            inductance_matrix=self.inductance_matrix,
            connectivity_matrix=self.connectivity_matrix,
        )

    @property
    def voltage_eigen_modes(self) -> Tuple[Tuple[float, ...], ...]:
        """Voltage eigenmodes (nodal voltages t_1..t_N) per eigenfrequency."""
        return self._sim._eigen_solver.compute_voltage_eigen_modes(
            capacitance_matrix=self.capacitance_matrix,
            inductance_matrix=self.inductance_matrix,
            connectivity_matrix=self.connectivity_matrix,
        )

    @property
    def current_eigen_modes(self) -> Tuple[Tuple[float, ...], ...]:
        """Current eigenmodes (segment currents) via I = -(j/w) L^-1 A^T V."""
        return self._sim._eigen_solver.compute_current_eigen_modes(
            capacitance_matrix=self.capacitance_matrix,
            inductance_matrix=self.inductance_matrix,
            connectivity_matrix=self.connectivity_matrix,
        )

    @property
    def node_arclengths(self) -> Tuple[float, ...]:
        """Arc length in meters from the grounded base to each discretization
        node t_0..t_N along the secondary centerline - length N+1, ascending
        from 0 to ``winding_length``.

        Derived from the discretizer's actual node parameters (not an assumed
        uniform spacing), so it stays correct for any discretization. These
        are the physical positions the voltage nodes sit at; the current
        segments sit at the midpoints between consecutive entries.
        """
        coil = self._sim.coil
        curve = coil.secondary.curve
        slices = self._sim._discretizer.get_slices(
            coil.secondary, coil.discretization_order
        )
        s = coil.unit_scale
        return tuple(
            curve.arc_length_between(curve.t_min, t) * s for t in slices
        )

    # -- Resonance and JavaTC-comparable lumped equivalents --------------------

    @property
    def resonant_frequency(self) -> float:
        """Fundamental (quarter-wave) resonant frequency in Hz."""
        return self.eigen_frequencies[0]

    @property
    def dc_inductance(self) -> float:
        """Ldc: low-frequency inductance in Henries.

        At DC the series winding carries a uniform current, so the total
        flux linkage per ampere is the sum of every mutual term:
        Ldc = sum_ij L_ij.
        """
        return float(np.sum(np.array(self.inductance_matrix)))

    @property
    def dc_capacitance(self) -> float:
        """Cdc: low-frequency (whole-coil-equipotential) capacitance in
        Farads.

        The all-ones quadratic form of the FULL nodal matrix - exact by
        the tent basis partition of unity (see derivation notebook).
        """
        C = np.array(self.nodal_capacitance_matrix)
        ones = np.ones(C.shape[0])
        return float(ones @ C @ ones)

    def _fundamental_mode(self) -> tuple[float, np.ndarray, np.ndarray]:
        """(omega, V, I) of the fundamental mode, V normalized so the
        physically meaningful magnitudes are positive."""
        omega = 2 * np.pi * self.resonant_frequency
        V = np.array(self.voltage_eigen_modes[0])
        I = np.array(self.current_eigen_modes[0])
        if V[-1] < 0:  # eigenvector sign is arbitrary; make V_top positive
            V, I = -V, -I
        return omega, V, I

    @property
    def effective_series_inductance(self) -> float:
        """Les: equivalent series inductance in Henries, referred to base
        current and top voltage (TSSP/JavaTC convention):
        V_top = omega * Les * I_base at resonance.
        """
        omega, V, I = self._fundamental_mode()
        return float(abs(V[-1]) / (omega * abs(I[0])))

    @property
    def effective_shunt_capacitance(self) -> float:
        """Ces: equivalent shunt capacitance in Farads - the capacitance
        that resonates with Les at the fundamental:
        Ces = 1 / (omega^2 * Les)."""
        omega = 2 * np.pi * self.resonant_frequency
        return float(1.0 / (omega ** 2 * self.effective_series_inductance))

    @property
    def energy_capacitance(self) -> float:
        """Cee: equivalent energy capacitance in Farads, referred to top
        voltage: Cee = (V^T C V) / V_top^2 with the fundamental voltage
        profile - twice the electric field energy per top-volt squared."""
        _, V, _ = self._fundamental_mode()
        C = np.array(self.capacitance_matrix)
        return float((V @ C @ V) / V[-1] ** 2)

    @property
    def energy_inductance(self) -> float:
        """Lee: the inductance that resonates with the energy capacitance
        at the fundamental: Lee = 1 / (omega^2 * Cee).

        This is the JavaTC/TSSP convention - one member of each lumped
        pair is energy-defined and the other derived, so that both
        (Les, Ces) and (Lee, Cee) resonate at f_res. Note the magnetic
        energy ratio I^T L I / I_base^2 is NOT this quantity: in the
        discrete eigensystem I^T L I = V^T C V exactly, which ties that
        ratio to Cee*(V_top/I_base)^2 instead.
        """
        omega = 2 * np.pi * self.resonant_frequency
        return float(1.0 / (omega ** 2 * self.energy_capacitance))

    @property
    def topload_effective_capacitance(self) -> float:
        """Effective (in-situ) capacitance of the topload group in Farads.

        The topload's share of the assembly's DC charge: the charge on the
        topload surfaces with the entire coil + topload at 1 V (the
        all-ones nodal profile, exact by partition of unity), i.e.
        C_top = sum_k q_k. Shielding by the coil, primary, ground and
        walls is included. This is the definition JavaTC's "Topload
        Effective Capacitance" uses (validated to 0.1% on the example
        coil); the fundamental-mode-weighted attribution gives a value
        ~8% higher and is NOT this quantity.
        """
        coil = self._sim.coil
        q_geo = np.array(self._sim._matrices.topload_charge_geo())
        s = coil.unit_scale
        return float(q_geo.sum()) * (2 * np.pi * epsilon_0 * s)

    # -- Derived scalars --------------------------------------------------------

    @property
    def winding_length(self) -> float:
        """Length of the winding along its central curve, in meters.

        (The coil form's wound extent - NOT the wire length; see
        conductor_length for the helical wire itself.)
        """
        coil = self._sim.coil
        curve = coil.secondary.curve
        return curve.arc_length_between(curve.t_min, curve.t_max) * coil.unit_scale

    @property
    def coil_pitch(self) -> float:
        """Center-to-center distance between adjacent turns, in meters."""
        return self.winding_length / self._sim.coil.secondary.total_turns

    @property
    def turns_per_length(self) -> float:
        """Winding density in turns per meter (average along the winding)."""
        return self._sim.coil.secondary.total_turns / self.winding_length

    @property
    def turn_spacing(self) -> float:
        """Edge-to-edge gap between adjacent turns, in meters."""
        coil = self._sim.coil
        wire_dia_m = 2 * coil.secondary.geometry.offset * coil.unit_scale
        return self.coil_pitch - wire_dia_m

    @property
    def mean_diameter(self) -> float:
        """Mean winding diameter (2x the average radius of the central
        curve), in meters."""
        coil = self._sim.coil
        curve = coil.secondary.curve
        ts = np.linspace(curve.t_min, curve.t_max, 512)
        mean_r = float(np.mean([curve.point_at(t)[0] for t in ts]))
        return 2 * mean_r * coil.unit_scale

    @property
    def aspect_ratio(self) -> float:
        """H/D aspect ratio: winding length over mean winding diameter."""
        return self.winding_length / self.mean_diameter

    @property
    def inclination_degrees(self) -> float:
        """Angle of the winding chord from horizontal, in degrees
        (90 for a straight vertical solenoid)."""
        coil = self._sim.coil
        curve = coil.secondary.curve
        r0, z0 = curve.point_at(curve.t_min)
        r1, z1 = curve.point_at(curve.t_max)
        return float(np.degrees(np.arctan2(z1 - z0, abs(r1 - r0))))

    @property
    def reactance_at_resonance(self) -> float:
        """The effective series reactance omega * Les at the fundamental,
        in Ohms."""
        omega = 2 * np.pi * self.resonant_frequency
        return omega * self.effective_series_inductance

    @property
    def skin_depth(self) -> float:
        """Skin depth of the secondary conductor at the fundamental
        resonant frequency, in meters: delta = 1/sqrt(pi*f*mu_0*sigma)."""
        conductivity = self._sim.coil.secondary.material.value.conductivity(self._AMBIENT_K)
        f = self.resonant_frequency
        return float(1.0 / np.sqrt(np.pi * f * mu_0 * conductivity))

    @property
    def conductor_length(self) -> float:
        """Total wire length of the secondary in meters.

        The winding is a helix whose centerline sweeps the secondary's
        curve while circling the axis total_turns times; its length is
        integrated numerically from the curve abstraction, so any
        secondary shape is supported.
        """
        from app.formulas.geometric import helical_wire_length

        coil = self._sim.coil
        length_geo = helical_wire_length(coil.secondary.curve, coil.secondary.turn_fxn)
        return length_geo * coil.unit_scale

    @property
    def dc_resistance(self) -> float:
        """DC resistance of the secondary wire in Ohms."""
        coil = self._sim.coil
        conductivity = coil.secondary.material.value.conductivity(self._AMBIENT_K)
        wire_dia_m = 2 * coil.secondary.geometry.offset * coil.unit_scale
        wire_area = np.pi * (wire_dia_m / 2) ** 2
        return float(self.conductor_length / (conductivity * wire_area))

    @property
    def wire_weight(self) -> float:
        """Mass of the secondary wire in kilograms."""
        coil = self._sim.coil
        wire_dia_m = 2 * coil.secondary.geometry.offset * coil.unit_scale
        wire_area = np.pi * (wire_dia_m / 2) ** 2
        density = coil.secondary.material.value.density
        return float(self.conductor_length * wire_area * density)

    @property
    def ac_resistance(self) -> float:
        """Effective AC resistance of the secondary at the fundamental, in
        Ohms: Rdc x skin-effect factor (exact Kelvin solution) x Medhurst
        proximity factor."""
        from app.formulas.resistance import medhurst_proximity_factor, skin_effect_factor

        coil = self._sim.coil
        wire_dia_m = 2 * coil.secondary.geometry.offset * coil.unit_scale
        skin = skin_effect_factor(wire_dia_m, self.skin_depth)
        proximity = medhurst_proximity_factor(
            spacing_ratio=self.coil_pitch / wire_dia_m,
            aspect_ratio=self.aspect_ratio,
        )
        return self.dc_resistance * skin * proximity

    @property
    def quality_factor(self) -> float:
        """Unloaded Q of the secondary at the fundamental:
        omega * Les / Rac."""
        return self.reactance_at_resonance / self.ac_resistance
