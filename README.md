# DATA23700 Final Project

**RQ1.** How strongly is mixed-use development associated with lower car ownership across U.S. metro neighborhoods,
and how does it compare with population density, street connectivity, and transit access once density and income are held fixed?

**RQ2.** Where do on-road CO2 emissions land relative to car ownership? Do car-light neighborhoods host more or less
traffic CO2 per km² than car-dependent ones? (Vulcan places emissions where driving happens, not where drivers live.)

Unit of analysis: 114,860 Census block groups in the 54 U.S. metros of 1M+ people.

## Figures
| File | Shows |
| --- | --- |
| `fig1_feature_comparison` | % of households with 2+ cars across percentiles of each feature (no controls) |
| `fig2_within_density` | Same, with each feature re-ranked inside density thirds |
| `fig3_within_density_income` | Same, inside 9 density × income groups; bands show the middle 50% of block groups |
| `fig4_gap_summary` | One gap per feature at each control level |
| `fig5_robustness` | Fig 4's strictest gap with within-metro ranking and a drive-alone commuting outcome |

## Repo layout
```
data/raw/         raw downloads (not committed, see below)
data/processed/   cleaned tables produced by src/ scripts (committed)
src/              data-prep scripts (build_sld, build_acs, build_vulcan)
docs/             working notes (Vulcan join handoff)
notebooks/        analysis notebooks (literate: text + code + figures)
figures/          exported charts (PNG + interactive HTML)
```

## Setup
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Reproduce
Run everything from the repo root, in this order.

1. Download the **EPA Smart Location Database v3.0** CSV into `data/raw/`:
   ```bash
   curl -L -o data/raw/EPA_SmartLocationDatabase_V3_Jan_2021_Final.csv \
     https://edg.epa.gov/EPADataCommons/public/OA/EPA_SmartLocationDatabase_V3_Jan_2021_Final.csv
   ```
2. Build the cleaned block-group table → `data/processed/sld_blockgroups.csv.gz`:
   ```bash
   python src/build_sld.py data/raw/EPA_SmartLocationDatabase_V3_Jan_2021_Final.csv
   ```
3. Pull ACS 2014-18 income and commute mode from the Census API → `data/processed/acs_blockgroups.csv.gz`.
   This output is committed, so you can skip this step. To rebuild it you need a free Census API key
   (https://api.census.gov/data/key_signup.html, then click the activation link in the email):
   ```bash
   export CENSUS_API_KEY=your_key_here
   python src/build_acs.py
   ```
   On a Mac, if you see `CERTIFICATE_VERIFY_FAILED`, run `"/Applications/Python 3.x/Install Certificates.command"` once.
4. Join Vulcan v4.0 on-road CO2 (see `docs/vulcan_handoff.md` for the download) → `data/processed/vulcan_onroad_*.csv.gz`:
   ```bash
   python src/build_vulcan.py data/raw/<vulcan on-road 2018 tif> blockgroup
   python src/build_vulcan.py data/raw/<vulcan on-road 2018 tif> tract
   ```
5. Open `notebooks/01_built_environment_vs_car_ownership.ipynb` and run all cells (Restart and Run All). Figures 1-5 are saved to `figures/`.

## Data sources
- U.S. EPA (2021). Smart Location Database v3.0 (block groups; ACS 2014-18, LEHD 2017, HERE 2018, GTFS 2020).
- U.S. Census Bureau. ACS 2014-2018 5-year estimates, tables B19013 and B08301 (joined on `geoid`).
- Gurney & Gawuc (2026). Vulcan: High-Resolution Annual Fossil Fuel CO2 Emissions in USA, 2010-2022 (v4.0). ORNL DAAC. https://doi.org/10.3334/ORNLDAAC/2505 (on-road sector, 2018, 1 km grid; joined spatially)
- U.S. Census Bureau. TIGER/Line 2019 block-group and tract boundaries (for the Vulcan join).

## Contribution statement
_Each member fills in their own line before submission (due Dec 4)._
- **Alex Guo:**
- **Saahil Chaddha:**
- **Aly Elkaffas:**
- **Matthew Quarles:**
