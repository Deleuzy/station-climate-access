import numpy as np

from sca.access import count_within


def test_counts_respect_radii():
    station = (0.0, 0.0)
    buildings = np.array([[300.0, 0.0], [0.0, 700.0], [0.0, 900.0], [-100.0, -100.0]])
    counts = count_within(station, buildings)
    assert counts == {400: 2, 800: 3}


def test_no_buildings_gives_zero():
    assert count_within((0.0, 0.0), np.empty((0, 2))) == {400: 0, 800: 0}


def test_boundary_is_inclusive():
    counts = count_within((0.0, 0.0), np.array([[800.0, 0.0]]))
    assert counts[800] == 1
