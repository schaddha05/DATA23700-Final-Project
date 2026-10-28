# DATA23700 Final Project

How mixed-use development, density, street connectivity, and transit access relate to car dependence across
U.S. metro neighborhoods, and how those patterns relate to on-road CO2 emissions.

## Repo layout
```
data/raw/         raw downloads (not committed, see below)
data/processed/   cleaned tables produced by src/ scripts (committed)
src/              data-prep scripts
notebooks/        analysis notebooks (literate: text + code + figures)
figures/          exported charts (PNG + interactive HTML)
```

## Setup
```bash
pip install -r requirements.txt
```

## Reproduce
1. Download the **EPA Smart Location Database v3.0** CSV
   (https://www.epa.gov/smartgrowth/smart-location-mapping) into `data/raw/`.
2. Build the cleaned block-group table:
   ```bash
   python src/build_sld.py data/raw/EPA_SmartLocationDatabase_V3_Jan_2021_Final.csv
   ```
   This writes `data/processed/sld_blockgroups.csv.gz`.
3. Open `notebooks/01_built_environment_vs_car_ownership.ipynb` and run all cells. Figures are saved to `figures/`.

## Data sources
- U.S. EPA (2021). Smart Location Database v3.0 (block groups; ACS 2014-18, LEHD 2017, HERE 2018, GTFS 2020).
- U.S. Census Bureau. ACS 2014-2018 5-year estimates (to be joined on `geoid`).
- Gurney & Gawuc (2026). Vulcan v4.0 on-road CO2 emissions, 1 km grid (to be joined spatially).
