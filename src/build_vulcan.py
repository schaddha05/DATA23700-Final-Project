"""Attach Vulcan v4.0 on-road CO2 emissions (1 km grid) to block groups or tracts.

Run from the repo root (after build_sld.py):
    python src/build_vulcan.py data/raw/<vulcan on-road 2018 GeoTIFF> blockgroup
    python src/build_vulcan.py data/raw/<vulcan on-road 2018 GeoTIFF> tract       # MAUP check

Writes:
    data/processed/vulcan_onroad_blockgroup.csv.gz   (or ..._tract.csv.gz)

Data:
  - Vulcan v4.0, ORNL DAAC dataset 2505 (Gurney & Gawuc 2026), https://doi.org/10.3334/ORNLDAAC/2505
    One GeoTIFF per sector per year. We want the ON-ROAD sector for 2018 (to match ACS 2014-18 / SLD).
    Pixel values: metric tons of CARBON per km2 per year (tC/km2/yr), nodata = -9999,
    Lambert conformal conic projection, 1 km x 1 km cells. Free NASA Earthdata login needed to download.
  - Census TIGER/Line 2019 block-group or tract polygons (downloaded automatically, one zip per state).
    2019 TIGER still uses 2010-vintage geographies, so GEOIDs match the SLD and ACS 2014-18.

Method (area-weighted zonal mean):
  1. Reproject the polygons to the raster's projection (we never resample the raster itself,
     so the emission values are not distorted).
  2. For each polygon, average the cells it overlaps, weighting each cell by the fraction of
     the cell the polygon covers (exactextract does this exactly). Result: tC/km2/yr.
  3. Convert carbon to CO2 (x 44/12), then derive
       - emissions per km2  (how much traffic CO2 happens IN the neighborhood)
       - emissions total    (per-km2 value x polygon area)
       - emissions per resident (total / population)

Known limitation (say this in the notebook + defense): many urban block groups are smaller than
one 1 km cell, so their value is mostly the value of the one or two cells they sit in, including
traffic on highways that pass through. That's the modifiable areal unit problem (MAUP). Re-running
at the tract level (bigger units, ~4 block groups each) tests whether conclusions depend on the unit.
"""

import sys
import urllib.request
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
from exactextract import exact_extract

SLD_PATH = "data/processed/sld_blockgroups.csv.gz"
TIGER_DIR = Path("data/raw/tiger")
TIGER_URL = {
    "blockgroup": "https://www2.census.gov/geo/tiger/TIGER2019/BG/tl_2019_{state}_bg.zip",
    "tract": "https://www2.census.gov/geo/tiger/TIGER2019/TRACT/tl_2019_{state}_tract.zip",
}
GEOID_LEN = {"blockgroup": 12, "tract": 11}
C_TO_CO2 = 44 / 12          # tons of carbon -> tons of CO2
EQUAL_AREA_CRS = "EPSG:5070"  # CONUS Albers equal-area, for polygon areas in km2


def load_sample(level: str) -> pd.DataFrame:
    """Analysis-sample units (1M+ metros, 50+ households) with population, at the chosen level."""
    sld = pd.read_csv(SLD_PATH, dtype={"geoid": str},
                      usecols=["geoid", "major_metro", "enough_households", "pop", "households"])
    sample = sld[sld["major_metro"] & sld["enough_households"]].copy()
    sample["geoid"] = sample["geoid"].str[: GEOID_LEN[level]]
    # For tracts, add up the sample block groups inside each tract.
    return sample.groupby("geoid", as_index=False)[["pop", "households"]].sum()


def load_polygons(level: str, states: list) -> gpd.GeoDataFrame:
    """Download (once) and read TIGER polygons for the given states."""
    TIGER_DIR.mkdir(parents=True, exist_ok=True)
    parts = []
    for state in states:
        url = TIGER_URL[level].format(state=state)
        local = TIGER_DIR / Path(url).name
        if not local.exists():
            print(f"  downloading {local.name}")
            urllib.request.urlretrieve(url, local)
        parts.append(gpd.read_file(local)[["GEOID", "geometry"]])
    return gpd.GeoDataFrame(pd.concat(parts, ignore_index=True), crs=parts[0].crs).rename(columns={"GEOID": "geoid"})


def zonal_emissions(raster_path: str, polys: gpd.GeoDataFrame) -> pd.DataFrame:
    """Area-weighted mean of the raster inside each polygon, plus derived per-km2 / total values.

    Returns one row per polygon with:
      onroad_tco2_per_km2   area-weighted mean emissions density (tCO2/km2/yr)
      area_km2              polygon area (equal-area projection)
      onroad_tco2_total     density x area (tCO2/yr attributed to the polygon)
      cells_covered_km2     how much raster area (with data) the polygon covered
    """
    with rasterio.open(raster_path) as src:
        raster_crs = src.crs
    polys = polys.copy()
    polys["area_km2"] = polys.to_crs(EQUAL_AREA_CRS).area / 1e6
    in_raster_crs = polys.to_crs(raster_crs)

    # "mean" = coverage-weighted mean (each cell weighted by the share of it inside the polygon);
    # "count" = sum of those coverage fractions = km2 of data-bearing cells covered (1 cell = 1 km2).
    stats = exact_extract(raster_path, in_raster_crs, ["mean", "count"],
                          include_cols=["geoid"], output="pandas")
    out = polys[["geoid", "area_km2"]].merge(stats, on="geoid", how="left")
    out["onroad_tco2_per_km2"] = out["mean"] * C_TO_CO2
    out["onroad_tco2_total"] = out["onroad_tco2_per_km2"] * out["area_km2"]
    out = out.rename(columns={"count": "cells_covered_km2"}).drop(columns="mean")
    return out


def main(raster_path: str, level: str = "blockgroup") -> None:
    if level not in GEOID_LEN:
        raise SystemExit(f"level must be one of {list(GEOID_LEN)}")
    out_path = f"data/processed/vulcan_onroad_{level}.csv.gz"

    sample = load_sample(level)
    states = sorted(sample["geoid"].str[:2].unique())
    print(f"{len(sample):,} {level}s in the analysis sample, {len(states)} states")

    polys = load_polygons(level, states)
    polys = polys[polys["geoid"].isin(sample["geoid"])]
    print(f"Matched polygons: {len(polys):,} of {len(sample):,}")

    result = zonal_emissions(raster_path, polys).merge(sample, on="geoid", how="left")
    result["onroad_tco2_per_resident"] = result["onroad_tco2_total"] / result["pop"].where(result["pop"] > 0)
    result["onroad_tco2_per_household"] = result["onroad_tco2_total"] / result["households"].where(result["households"] > 0)

    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(out_path, index=False, compression="gzip")
    print(f"Wrote {out_path} ({len(result):,} rows)")
    print(result[["area_km2", "onroad_tco2_per_km2", "onroad_tco2_per_resident"]].describe().round(2))
    print(f"Missing emissions: {result['onroad_tco2_per_km2'].isna().mean():.1%}")
    print(f"Smaller than one 1 km cell: {(result['area_km2'] < 1).mean():.0%}  <- MAUP exposure")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    main(*sys.argv[1:])
