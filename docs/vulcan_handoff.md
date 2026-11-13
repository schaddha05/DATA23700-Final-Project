# Vulcan CO2 join: handoff

**Goal:** give every block group in our sample an on-road CO2 number (per km² and per resident), so we can answer RQ part 2: do lower-car neighborhoods have lower on-road CO2?

`src/build_vulcan.py` is written and its math is tested on synthetic data. What's left is running it on the real files and sanity-checking the output. Target: **done by Sun Nov 22**, so we have a week to build figures before defenses.

## 1. Setup (one time)

```bash
cd DATA23700-Final-Project
git pull
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt       # now includes geopandas, rasterio, exactextract
```

## 2. Get the Vulcan file

1. Make a free NASA Earthdata account: https://urs.earthdata.nasa.gov/users/new
2. Open the dataset page: https://doi.org/10.3334/ORNLDAAC/2505 (Vulcan v4.0, Gurney & Gawuc 2026)
3. Download the **on-road**, **contiguous US**, **1 km**, **2018** GeoTIFF. Files are named like
   `v4.<sector>.co2.<domain>.1km.lcc.mn.<year>.tif`, so look for the `onr` sector, `usa` domain, `2018`.
   Check the exact name in the user guide's file table.
4. Save it in `data/raw/` (gitignored, don't commit it).

Quick sanity check in Python:

```python
import rasterio
with rasterio.open("data/raw/<file>.tif") as src:
    print(src.crs, src.res, src.nodata, src.shape)
```

Expect a Lambert conformal conic CRS, `(1000.0, 1000.0)` resolution, nodata `-9999`.

## 3. Run it

```bash
python src/build_vulcan.py data/raw/<file>.tif blockgroup
python src/build_vulcan.py data/raw/<file>.tif tract
```

The first run downloads Census TIGER 2019 polygons for 40 states into `data/raw/tiger/` (a few hundred MB, one time). Outputs:
- `data/processed/vulcan_onroad_blockgroup.csv.gz`
- `data/processed/vulcan_onroad_tract.csv.gz`

## 4. Check the output before we use it

- [ ] "Matched polygons" ≈ 114,860 for block groups (Puerto Rico's ~1,600 San Juan block groups will have no emissions, since Vulcan covers CONUS + Alaska only. That's expected; note it.)
- [ ] Missing emissions % is small apart from Puerto Rico
- [ ] Emissions per km² are higher in dense urban cores and along highways (map one metro to eyeball it)
- [ ] Per-resident numbers are in a plausible range (a few tCO2 per person per year from on-road is typical in the U.S. Flag anything way off)
- [ ] Note the "smaller than one 1 km cell" % it prints. That number goes in our limitations

## 5. Things to be ready to explain in the defense

- **Units:** Vulcan is in tons of *carbon*. We multiply by 44/12 to get tons of CO2.
- **Why area-weighted:** a block group that covers 30% of a cell gets 30% of that cell's weight in its average.
- **Why we reproject polygons, not the raster:** resampling the raster would change emission values.
- **MAUP:** many urban block groups are smaller than one cell, so highway traffic passing through gets assigned to whoever lives next to it. The tract-level run checks whether conclusions change with bigger units.
- **Per km² vs per resident:** per km² = how much traffic CO2 happens *in* a place (exposure). Per resident = how much CO2 a place's population is plausibly responsible for. These can point in opposite directions, and that's one of our hypotheses.

Questions → group chat. Alex has the context on the SLD side.
