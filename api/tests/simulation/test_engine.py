"""
Unit tests for the Tesla coil simulation engine (abstract base class).

Run with: pytest tests/simulation/test_engine.py -v
"""
import pytest
from app.simulation.engine import TeslaCoilSimulationEngine


class TestTeslaCoilSimulationEngine:
    """Tests for the TeslaCoilSimulationEngine abstract base class."""

    def test_cannot_instantiate_directly(self):
        """The ABC should not be instantiable."""
        with pytest.raises(TypeError):
            TeslaCoilSimulationEngine()

    def test_requires_compute_capacitance_matrix(self):
        """A subclass missing compute_capacitance_matrix should not be instantiable."""

        class Incomplete(TeslaCoilSimulationEngine):
            def compute_inductance_matrix(self, *a, **kw):
                pass
            def compute_connectivity_matrix(self):
                pass
            def compute_eigen_frequency_family(self, *a, **kw):
                pass

        with pytest.raises(TypeError):
            Incomplete()

    def test_requires_compute_inductance_matrix(self):
        """A subclass missing compute_inductance_matrix should not be instantiable."""

        class Incomplete(TeslaCoilSimulationEngine):
            def compute_capacitance_matrix(self, *a, **kw):
                pass
            def compute_connectivity_matrix(self):
                pass
            def compute_eigen_frequency_family(self, *a, **kw):
                pass

        with pytest.raises(TypeError):
            Incomplete()

    def test_requires_compute_connectivity_matrix(self):
        """A subclass missing compute_connectivity_matrix should not be instantiable."""

        class Incomplete(TeslaCoilSimulationEngine):
            def compute_capacitance_matrix(self, *a, **kw):
                pass
            def compute_inductance_matrix(self, *a, **kw):
                pass
            def compute_eigen_frequency_family(self, *a, **kw):
                pass

        with pytest.raises(TypeError):
            Incomplete()

    def test_requires_compute_eigen_frequency_family(self):
        """A subclass missing compute_eigen_frequency_family should not be instantiable."""

        class Incomplete(TeslaCoilSimulationEngine):
            def compute_capacitance_matrix(self, *a, **kw):
                pass
            def compute_inductance_matrix(self, *a, **kw):
                pass
            def compute_connectivity_matrix(self):
                pass

        with pytest.raises(TypeError):
            Incomplete()

    def test_complete_subclass_instantiable(self):
        """A complete concrete subclass should be instantiable."""

        class Complete(TeslaCoilSimulationEngine):
            def compute_capacitance_matrix(self, *a, **kw):
                return ()
            def compute_inductance_matrix(self, *a, **kw):
                return ()
            def compute_connectivity_matrix(self):
                return ()
            def compute_eigen_frequency_family(self, *a, **kw):
                return None

        engine = Complete()
        assert isinstance(engine, TeslaCoilSimulationEngine)
