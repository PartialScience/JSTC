from typing import Tuple
from app.simulation.types import EigenFamily
import numpy as np
from scipy import linalg
import methodtools as mt

class EigenFrequencySolver:
    """Class responsible for solving eigenfrequency problems for Tesla coil systems."""
    
    @mt.lru_cache()
    @staticmethod
    def compute_eigen_frequency_family(
        capacitance_matrix: Tuple[Tuple[float, ...], ...], 
        inductance_matrix: Tuple[Tuple[float, ...], ...], 
        connectivity_matrix: Tuple[Tuple[float, ...], ...]                               
    ) -> EigenFamily:
        """
        Solve the generalized eigenvalue problem for the system:
        ω² C V = -A L⁻¹ Aᵀ V
        
        Args:
            capacitance_matrix: Capacitance matrix (C)
            inductance_matrix: Inductance matrix (L)
            connectivity_matrix: Connectivity matrix (A)
            
        Returns:
            EigenFamily with eigenfrequencies (ω) and voltage eigenmodes (V)
        """
        # Convert tuples to numpy arrays
        C = np.array(capacitance_matrix)
        L = np.array(inductance_matrix)
        A = np.array(connectivity_matrix)
        
        # Compute the right-hand side matrix: -A L⁻¹ Aᵀ
        L_inv = linalg.inv(L)
        RHS = -A @ L_inv @ A.T
        
        # Solve generalized eigenvalue problem: ω² C V = RHS V
        # This is equivalent to: RHS V = ω² C V
        eigenvalues, eigenvectors = linalg.eig(RHS, C)
        
        # Extract real parts and compute frequencies from ω²
        # ω² is the eigenvalue, so ω = sqrt(eigenvalue)
        # f = ω / (2π)
        omega_squared = np.real(eigenvalues)
        omega = np.sqrt(np.abs(omega_squared))
        frequencies = omega / (2 * np.pi)
        
        # Sort by frequency (ascending)
        sorted_indices = np.argsort(frequencies)
        frequencies_sorted = frequencies[sorted_indices]
        eigenvectors_sorted = np.real(eigenvectors[:, sorted_indices])
        
        # Convert to lists for the return type
        freq_list = frequencies_sorted.tolist()
        eigvec_list = [eigenvectors_sorted[:, i].tolist() for i in range(eigenvectors_sorted.shape[1])]
        
        return EigenFamily(
            eigenvalues=freq_list,
            eigenvectors=eigvec_list
        )

class CurrentEigenModeSolver:
    """Class responsible for solving eigencurrent modes from the voltage modes and eigen values."""
    
    @mt.lru_cache()
    @staticmethod
    def find_current_modes_from_inductance(
        inverse_inductance_matrix: Tuple[Tuple[float, ...], ...], 
        transpose_connectivity_matrix: Tuple[Tuple[float, ...], ...],
        eigen_frequencies: Tuple[float, ...],
        voltage_eigenmodes: Tuple[Tuple[float, ...], ...]
    ) -> Tuple[Tuple[float, ...], ...]:
        """
        Compute current eigenmodes from voltage eigenmodes using the inductance matrix.
        
        In a standard LC circuit, this is the equivalent of finding current by I = V / (jωL).
        
        Here we solve: 
        I = -(j/ω) L⁻¹ Aᵀ V
        
        Args:
            inverse_inductance_matrix: Inverse inductance matrix (L⁻¹)
            transpose_connectivity_matrix: Transpose of the connectivity matrix (Aᵀ)
            eigen_frequencies: Eigenfrequencies (ω)
            voltage_eigenmodes: Voltage eigenmodes (V)
    """
    
        # Convert tuples to numpy arrays
        L_inv = np.array(inverse_inductance_matrix)
        A_T = np.array(transpose_connectivity_matrix)
        V = np.array(voltage_eigenmodes).T  # Shape: (num_nodes, num_modes)
        
        num_modes = V.shape[1]
        I_modes = []
        
        for i in range(num_modes):
            omega = 2 * np.pi * eigen_frequencies[i]
            V_mode = V[:, i]
            
            # Compute current mode: I = -(j/ω) L⁻¹ Aᵀ V
            I_mode = -(1j / omega) * L_inv @ A_T @ V_mode
            
            I_modes.append(np.real(I_mode).tolist())
        
        return tuple(tuple(mode) for mode in I_modes)