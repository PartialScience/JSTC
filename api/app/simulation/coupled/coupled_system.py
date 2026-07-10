"""
The coupled primary-secondary electrical system, in SI units.

State variables (time domain):

    V   - secondary nodal voltages (N)   [on the reduced capacitance nodes]
    I   - secondary segment currents (N)
    i_p - primary current (scalar)
    v_c - primary tank-capacitor voltage (scalar)

Lossless equations of motion (resistances enter the impedance sweep only):

    (1)  C V'            =  A I
    (2)  L I' + m i_p'   = -A^T V
    (3)  L_p i_p' + m^T I' = -v_c
    (4)  C_p v_c'        =  i_p

Equations (2) and (3) are the bordered inductance system
[[L, m], [m^T, L_p]] acting on [I', i_p']. This is exactly the magnetic
object CouplingView exposes; here it is closed with the tank capacitor
(4) and the secondary capacitance ladder (1). The derivation and sign
conventions match docs/cmatrix_derivation.ipynb (secondary) extended with
the primary loop discussed in the design notes.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy import linalg


@dataclass(frozen=True)
class CoupledSystem:
    """SI matrices defining the coupled system.

    Attributes:
        capacitance: reduced NxN secondary nodal capacitance C [F].
        inductance: NxN secondary segment inductance L [H].
        connectivity: NxN series connectivity A.
        coupling: length-N primary-secondary coupling vector m [H].
        primary_inductance: primary self-inductance L_p [H] (winding + leads).
        tank_capacitance: primary tank capacitance C_p [F].
    """

    capacitance: np.ndarray
    inductance: np.ndarray
    connectivity: np.ndarray
    coupling: np.ndarray
    primary_inductance: float
    tank_capacitance: float

    def __post_init__(self):
        n = self.capacitance.shape[0]
        for name, arr, shape in (
            ("capacitance", self.capacitance, (n, n)),
            ("inductance", self.inductance, (n, n)),
            ("connectivity", self.connectivity, (n, n)),
            ("coupling", self.coupling, (n,)),
        ):
            if arr.shape != shape:
                raise ValueError(f"{name} has shape {arr.shape}, expected {shape}")
        if self.tank_capacitance <= 0:
            raise ValueError("tank_capacitance must be positive for a coupled solve")

    @property
    def order(self) -> int:
        """N, the number of secondary segments."""
        return self.capacitance.shape[0]

    def bordered_inductance(self) -> np.ndarray:
        """The (N+1)x(N+1) combined inductance [[L, m], [m^T, L_p]]."""
        n = self.order
        Lb = np.empty((n + 1, n + 1))
        Lb[:n, :n] = self.inductance
        Lb[:n, n] = self.coupling
        Lb[n, :n] = self.coupling
        Lb[n, n] = self.primary_inductance
        return Lb


def _state_matrix(sys: CoupledSystem) -> np.ndarray:
    """Assemble M for x' = M x with x = [V, I, i_p, v_c]."""
    n = sys.order
    C = sys.capacitance
    A = sys.connectivity
    Cp = sys.tank_capacitance

    Lb = sys.bordered_inductance()
    Winv = linalg.inv(Lb)                      # (N+1)x(N+1)

    # Forcing of [I'; i_p'] by V:  [[-A^T], [0]]  -> (N+1)xN
    F_V = np.zeros((n + 1, n))
    F_V[:n, :] = -A.T
    dcurr_dV = Winv @ F_V                       # (N+1)xN

    # Forcing of [I'; i_p'] by v_c: [0...0, -1]^T -> (N+1)
    dcurr_dvc = Winv[:, n] * (-1.0)             # (N+1)

    M = np.zeros((2 * n + 2, 2 * n + 2))
    # Index layout: V = [0:n], I = [n:2n], i_p = 2n, v_c = 2n+1
    iV = slice(0, n)
    iI = slice(n, 2 * n)
    iip = 2 * n
    ivc = 2 * n + 1

    # V' = C^-1 A I
    M[iV, iI] = linalg.solve(C, A, assume_a="pos")

    # I'  = dcurr_dV[:n] V + dcurr_dvc[:n] v_c
    M[iI, iV] = dcurr_dV[:n, :]
    M[iI, ivc] = dcurr_dvc[:n]
    # i_p' = dcurr_dV[n] V + dcurr_dvc[n] v_c
    M[iip, iV] = dcurr_dV[n, :]
    M[iip, ivc] = dcurr_dvc[n]

    # v_c' = i_p / C_p
    M[ivc, iip] = 1.0 / Cp

    return M


def coupled_mode_frequencies(sys: CoupledSystem) -> np.ndarray:
    """Resonant frequencies (Hz) of the coupled system, ascending.

    The eigenvalues of the lossless state matrix are conjugate pairs
    +/- j*omega; each physical mode is one positive omega. The two lowest
    are the split fundamental pair (primary/secondary pole splitting).
    """
    M = _state_matrix(sys)
    eigs = linalg.eigvals(M)
    # Keep positive imaginary parts (one per conjugate pair)
    freqs = np.abs(eigs.imag) / (2 * np.pi)
    freqs = freqs[eigs.imag > 0]
    return np.sort(freqs)


@dataclass
class DrivenResponse:
    """Steady-state phasor response to a sinusoidal primary drive.

    All phasors are referenced to the primary current (taken as the phase
    reference). Multiply by ``exp(j w t)`` and take the real part for the
    instantaneous waveform.

    Attributes:
        omega: Drive angular frequency [rad/s].
        primary_current: The drive phasor I_p [A] (the reference).
        segment_currents: Secondary segment currents I [A], length N.
        node_voltages: Secondary nodal voltages for the free nodes
            t_1..t_N [V], length N. The grounded base node t_0 is 0 and is
            not included; prepend 0 for the full t_0..t_N vector.
        primary_voltage: The primary winding EMF V_p [V] - the end-to-end
            differential voltage that drives the primary potential profile.
    """

    omega: float
    primary_current: complex
    segment_currents: np.ndarray
    node_voltages: np.ndarray
    primary_voltage: complex


def primary_driven_response(
    sys: CoupledSystem,
    frequency_hz: float,
    primary_current: complex = 1.0,
    secondary_resistance: float = 0.0,
    primary_resistance: float = 0.0,
) -> DrivenResponse:
    """Solve the coupled system's steady-state phasors for a primary drive.

    Drives the primary with current phasor ``primary_current`` at
    ``frequency_hz`` and returns the resulting secondary currents and node
    voltages and the primary EMF - the operating state the field
    visualization superposes into a real field. Phasor derivation (same
    conventions as primary_input_impedance):

        K(w)  = j w L + R_s/N I + (1/(j w)) A^T C^-1 A
        I     = -j w I_p K^-1 m                        (segment currents)
        V     = (1/(j w)) C^-1 A I                     (node voltages)
        V_p   = (j w L_p + R_p) I_p + j w m^T I        (primary EMF)

    Note V_p / I_p equals the winding driving-point impedance
    (primary_input_impedance with include_tank=False), a useful cross-check.

    Args:
        sys: The coupled system.
        frequency_hz: Drive frequency [Hz].
        primary_current: Primary current phasor [A] (magnitude sets scale;
            its phase is the reference).
        secondary_resistance: Total secondary AC resistance [Ohm], spread
            equally across segments (finite response at resonance).
        primary_resistance: Primary series resistance [Ohm].

    Returns:
        The DrivenResponse phasors.
    """
    n = sys.order
    C = sys.capacitance
    L = sys.inductance
    A = sys.connectivity
    m = sys.coupling
    Lp = sys.primary_inductance

    w = 2 * np.pi * frequency_hz
    Ip = complex(primary_current)

    AtCinvA = A.T @ linalg.solve(C, A, assume_a="pos")
    R_seg = (secondary_resistance / n) * np.eye(n)
    K = 1j * w * L + R_seg + (1.0 / (1j * w)) * AtCinvA

    I = -1j * w * Ip * linalg.solve(K, m)
    V = (1.0 / (1j * w)) * linalg.solve(C, A @ I, assume_a="pos")
    Vp = (1j * w * Lp + primary_resistance) * Ip + 1j * w * (m @ I)

    return DrivenResponse(
        omega=w,
        primary_current=Ip,
        segment_currents=I,
        node_voltages=V,
        primary_voltage=Vp,
    )


def primary_input_impedance(
    sys: CoupledSystem,
    frequencies_hz: np.ndarray,
    secondary_resistance: float = 0.0,
    primary_resistance: float = 0.0,
    include_tank: bool = True,
) -> np.ndarray:
    """Driving-point impedance looking into the primary, per frequency.

    Derivation (phasor form, driving the primary with current i_p):

        K(omega) = j*omega*L + R_s/N * I  +  (1/(j*omega)) A^T C^-1 A
        Z_winding = R_p + j*omega*L_p + omega^2 * m^T K^-1 m
        Z_input   = Z_winding + 1/(j*omega*C_p)      (if include_tank)

    The reflected term omega^2 m^T K^-1 m peaks where the secondary ladder
    resonates (K near singular), so the split resonances appear as
    features in |Z|. Resistances make the peaks finite; omit them
    (default) for the ideal lossless impedance.

    Args:
        sys: The coupled system.
        frequencies_hz: Frequencies to evaluate (Hz).
        secondary_resistance: Total secondary AC resistance [Ohm],
            distributed equally across the N segments.
        primary_resistance: Primary series resistance [Ohm].
        include_tank: Add the series tank capacitor 1/(j*omega*C_p). When
            False, returns the impedance of the primary winding + reflected
            secondary alone (the tank cap left for the caller to add).

    Returns:
        Complex impedance array, same length as frequencies_hz [Ohm].
    """
    n = sys.order
    C = sys.capacitance
    L = sys.inductance
    A = sys.connectivity
    m = sys.coupling
    Lp = sys.primary_inductance
    Cp = sys.tank_capacitance

    AtCinvA = A.T @ linalg.solve(C, A, assume_a="pos")
    R_seg = (secondary_resistance / n) * np.eye(n)

    out = np.empty(len(frequencies_hz), dtype=complex)
    for idx, f in enumerate(frequencies_hz):
        w = 2 * np.pi * f
        K = 1j * w * L + R_seg + (1.0 / (1j * w)) * AtCinvA
        reflected = w ** 2 * (m @ linalg.solve(K, m))
        z = primary_resistance + 1j * w * Lp + reflected
        if include_tank:
            z += 1.0 / (1j * w * Cp)
        out[idx] = z
    return out
