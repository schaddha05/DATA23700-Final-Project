# DATA23700 Final Project

## Project Summary
The geographic separation of residential, commercial, and employment areas in many American cities has contributed to widespread automobile dependence, raising concerns about transportation accessibility and the quality of urban environments. Our project investigates how strongly mixed-use development is associated with reduced car dependence across major U.S. metropolitan areas and how this relationship compares with other characteristics including population density, street connectivity, and public transportation accessibility. Using data from the EPA's Smart Location Database and the U.S. Census Bureau's American Community Survey, we use household vehicle ownership as a proxy for car dependence, primarily examining the proportion of households owning two or more vehicles. Through interactive visualizations and comparative analysis, we explore these relationships while accounting for socioeconomic factors such as household income. Our goal is to identify which characteristics of urban development are most strongly associated with reduced automobile dependence and provide insight into how American cities can create more accessible, walkable, and connected environments where driving is an option rather than a necessity.

**Research question.** How strongly is mixed-use development associated with reduced car dependence across major U.S. metropolitan city areas, and how does this relationship compare with other characteristics of the built environment, such as population density, street connectivity, and public transportation accessibility?

Unit of analysis: 114,860 Census block groups in the 54 U.S. metros of 1M+ people.

## Figures
| File | Shows |
| --- | --- |
| `fig1_feature_comparison` | % of households with 2+ cars across percentiles of each feature (no controls) |
| `fig2_within_density` | Same, with each feature re-ranked inside density thirds |
| `fig3_within_density_income` | Same, inside 9 density × income groups; bands show the middle 50% of block groups |
| `fig4_gap_summary` | One gap per feature at each control level |
| `fig5_robustness` | Fig 4's strictest gap with within-metro ranking and a drive-alone commuting outcome |
| `fig6_commuting_balance` | Fig 4's strictest car-ownership gaps across groups defined by jobs per resident worker |
| `fig7_residual_by_mixed_use` | Residual from a model of density, income, transit and connectivity, by mixed-use percentile |
| `fig8_residual_map_chicago` | Map of model residuals next to mixed use, Cook County (Chicago) |
| `fig8b_residual_map_chicago_metro` | Same map for the full Chicago metro, for comparison (saved only) |

## Repo layout
```
data/raw/         raw downloads (not committed, see below)
data/processed/   cleaned tables produced by src/ scripts (committed)
src/              data-prep scripts (build_sld, build_acs)
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
4. Download the **2018 Census block group boundaries** for the Chicago metro states into `data/raw/` (leave them zipped). Only needed for the Step 10 maps:
   ```bash
   curl -o data/raw/cb_2018_17_bg_500k.zip https://www2.census.gov/geo/tiger/GENZ2018/shp/cb_2018_17_bg_500k.zip
   curl -o data/raw/cb_2018_18_bg_500k.zip https://www2.census.gov/geo/tiger/GENZ2018/shp/cb_2018_18_bg_500k.zip
   curl -o data/raw/cb_2018_55_bg_500k.zip https://www2.census.gov/geo/tiger/GENZ2018/shp/cb_2018_55_bg_500k.zip
   ```
5. Open `notebooks/01_built_environment_vs_car_ownership.ipynb` and run all cells (Restart and Run All). Figures 1–8 are saved to `figures/`.

## Data sources
- U.S. EPA (2021). Smart Location Database v3.0 (block groups; ACS 2014-18, LEHD 2017, HERE 2018, GTFS 2020).
- U.S. Census Bureau. ACS 2014-2018 5-year estimates, tables B19013 and B08301 (joined on `geoid`).
- U.S. Census Bureau. 2018 cartographic boundary files, block groups (Illinois, Indiana, Wisconsin), for the Step 10 maps.

## Contribution statement
_Each member fills in their own line before submission (due Dec 4)._
- **Alex Guo:**
- **Saahil Chaddha:**
- **Aly Elkaffas:** Step 10: residual model, Fig 7 (residual by mixed use), Fig 8 (Cook County residual map) and the supporting checks; README and requirements updates.
- **Matthew Quarles:**
