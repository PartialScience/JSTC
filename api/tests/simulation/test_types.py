"""
Unit tests for the EigenFamily dataclass.

Run with: pytest tests/simulation/test_types.py -v
"""
import pytest
from app.simulation.types import EigenFamily


class TestEigenFamily:
    """Tests for the EigenFamily dataclass."""

    def test_creation(self):
        """Test that an EigenFamily can be created with valid data."""
        ef = EigenFamily(
            eigenvalues=(1.0, 2.0, 3.0),
            eigenvectors=((1.0, 0.0), (0.0, 1.0), (0.5, 0.5)),
        )
        assert ef.eigenvalues == (1.0, 2.0, 3.0)
        assert ef.eigenvectors == ((1.0, 0.0), (0.0, 1.0), (0.5, 0.5))

    def test_empty(self):
        """Test that an EigenFamily can be created with empty tuples."""
        ef = EigenFamily(eigenvalues=(), eigenvectors=())
        assert ef.eigenvalues == ()
        assert ef.eigenvectors == ()

    def test_single_mode(self):
        """Test an EigenFamily with a single eigenvalue/eigenvector pair."""
        ef = EigenFamily(
            eigenvalues=(42.0,),
            eigenvectors=((1.0, 0.0, 0.0),),
        )
        assert len(ef.eigenvalues) == 1
        assert len(ef.eigenvectors) == 1

    def test_equality(self):
        """Test that two EigenFamilies with equal data are equal."""
        ef1 = EigenFamily(eigenvalues=(1.0,), eigenvectors=((1.0,),))
        ef2 = EigenFamily(eigenvalues=(1.0,), eigenvectors=((1.0,),))
        assert ef1 == ef2

    def test_inequality(self):
        """Test that EigenFamilies with different data are not equal."""
        ef1 = EigenFamily(eigenvalues=(1.0,), eigenvectors=((1.0,),))
        ef2 = EigenFamily(eigenvalues=(2.0,), eigenvectors=((1.0,),))
        assert ef1 != ef2
