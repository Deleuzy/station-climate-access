from sca.terrain import tile_name, tile_urls_for_bbox


def test_tile_names_north_east():
    assert tile_name(56, 10) == "N56_00_E010_00"
    assert tile_name(55, 12) == "N55_00_E012_00"


def test_tile_names_south_west():
    assert tile_name(-1, -3) == "S01_00_W003_00"


def test_bbox_inside_one_tile_gives_one_url():
    urls = tile_urls_for_bbox(56.1, 10.1, 56.3, 10.4)
    assert len(urls) == 1
    assert urls[0].endswith("Copernicus_DSM_COG_10_N56_00_E010_00_DEM/Copernicus_DSM_COG_10_N56_00_E010_00_DEM.tif")
    assert urls[0].startswith("/vsicurl/https://copernicus-dem-30m.s3.amazonaws.com/")


def test_bbox_across_tiles_gives_each_tile():
    assert len(tile_urls_for_bbox(55.9, 11.9, 56.1, 12.1)) == 4
