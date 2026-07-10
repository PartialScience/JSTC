import numpy as np
import pytest

from app.simulation.fields import FieldGrid


class TestFieldGrid:
    def test_shape_and_coords(self):
        g = FieldGrid.over_domain(r_max=10, z_max=20, nr=5, nz=7)
        assert g.shape == (7, 5)
        assert g.r_coords[0] == 0 and g.r_coords[-1] == 10
        assert g.z_coords[0] == 0 and g.z_coords[-1] == 20

    def test_points_layout_matches_shape(self):
        g = FieldGrid.over_domain(r_max=2, z_max=3, nr=3, nz=4)
        pts = g.points()  # (2, 12)
        assert pts.shape == (2, 12)
        # Row-major (z outer, r inner): reshape recovers meshgrid.
        rr = pts[0].reshape(g.shape)
        zz = pts[1].reshape(g.shape)
        assert np.allclose(rr[0], g.r_coords)  # first z-row spans all r
        assert np.allclose(zz[:, 0], g.z_coords)  # first r-col spans all z

    def test_validation(self):
        with pytest.raises(ValueError):
            FieldGrid.over_domain(1, 1, nr=1, nz=5)
        with pytest.raises(ValueError):
            FieldGrid(r_min=1, r_max=0, z_min=0, z_max=1, nr=3, nz=3)
