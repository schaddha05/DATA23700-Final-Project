"""Build a clean, slim block-group table from the EPA Smart Location Database (SLD) v3.0.

Run from the repo root:
    python src/build_sld.py data/raw/EPA_SmartLocationDatabase_V3_Jan_2021_Final.csv

Writes:
    data/processed/sld_blockgroups.csv.gz   (small enough to commit to GitHub)

What it does:
  1. Reads only the ~25 SLD columns we need (the full file is several hundred MB).
  2. Converts the SLD's missing-value code (-99999) to NaN.
  3. Builds a 12-digit block-group ID ("geoid") for joining to Census ACS data later.
  4. Puts car-ownership shares on a 0-100 scale.
  5. Adds flags we filter on in the notebook (metro area, major metro, enough households).
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

# SLD column name -> our column name
COLUMNS = {
    "STATEFP": "statefp",
    "COUNTYFP": "countyfp",
    "TRACTCE": "tractce",
    "BLKGRPCE": "blkgrpce",
    "CBSA": "cbsa",
    "CBSA_Name": "cbsa_name",
    "CBSA_POP": "cbsa_pop",
    "Ac_Land": "acres_land",
    "TotPop": "pop",
    "HH": "households",
    "Pct_AO0": "pct_0_cars",
    "Pct_AO1": "pct_1_car",
    "Pct_AO2p": "pct_2plus_cars",
    "R_PCTLOWWAGE": "low_wage_share",
    "D1A": "housing_density",       # housing units / acre (unprotected land)
    "D1B": "pop_density",           # people / acre (unprotected land)
    "D2A_EPHHM": "mixed_use",       # job + household entropy, 0 = single use, 1 = even mix
    "D3B": "intersection_density",  # street connectivity, intersections / sq mi
    "D4A": "transit_dist_m",        # walking distance (m) to nearest transit stop
    "D4C": "transit_freq",          # evening-peak transit trips / hour within 1/4 mile
    "NatWalkInd": "walk_index",     # EPA National Walkability Index (1-20)
}

ID_COLS = ["statefp", "countyfp", "tractce", "blkgrpce", "cbsa", "cbsa_name"]
MISSING_CODE = -99999
MAJOR_METRO_POP = 1_000_000   # "major metro" = metro area of 1M+ people
MIN_HOUSEHOLDS = 50           # below this, car-ownership shares are too noisy


def main(raw_path: str, out_path: str = "data/processed/sld_blockgroups.csv.gz") -> None:
    # Match column names case-insensitively (SLD capitalization varies between releases).
    header = pd.read_csv(raw_path, nrows=0).columns
    lookup = {c.lower(): c for c in header}
    missing = [c for c in COLUMNS if c.lower() not in lookup]
    if missing:
        raise SystemExit(f"These SLD columns were not found: {missing}")
    usecols = [lookup[c.lower()] for c in COLUMNS]
    rename = {lookup[c.lower()]: new for c, new in COLUMNS.items()}

    df = pd.read_csv(
        raw_path,
        usecols=usecols,
        dtype={lookup[c.lower()]: str for c in ["STATEFP", "COUNTYFP", "TRACTCE", "BLKGRPCE", "CBSA"]},
        low_memory=False,
    ).rename(columns=rename)
    print(f"Read {len(df):,} block groups")

    # 1. Missing-value code -> NaN. For transit distance, -99999 has a meaning:
    #    "no transit stop within 3/4 mile", so we keep that as its own flag first.
    df["no_stop_within_3_4mi"] = df["transit_dist_m"].eq(MISSING_CODE)
    num_cols = [c for c in df.columns if c not in ID_COLS and df[c].dtype != bool]
    df[num_cols] = df[num_cols].apply(pd.to_numeric, errors="coerce").replace(MISSING_CODE, np.nan)

    # 2. 12-digit block-group FIPS code (state 2 + county 3 + tract 6 + block group 1).
    df["geoid"] = (
        df["statefp"].str.zfill(2)
        + df["countyfp"].str.zfill(3)
        + df["tractce"].str.zfill(6)
        + df["blkgrpce"].str[-1]
    )

    # 3. Car-ownership shares on a 0-100 scale (SLD stores them as 0-1 fractions).
    for c in ["pct_0_cars", "pct_1_car", "pct_2plus_cars"]:
        if df[c].max() <= 1.0001:
            df[c] = df[c] * 100

    # 4. Flags used for filtering in the notebook.
    df["in_metro"] = df["cbsa_name"].notna() & df["cbsa_name"].str.strip().ne("")
    df["major_metro"] = df["in_metro"] & (df["cbsa_pop"] >= MAJOR_METRO_POP)
    df["enough_households"] = df["households"] >= MIN_HOUSEHOLDS

    df = df.drop(columns=["statefp", "countyfp", "tractce", "blkgrpce"])
    front = ["geoid", "cbsa", "cbsa_name", "cbsa_pop", "in_metro", "major_metro", "enough_households"]
    df = df[front + [c for c in df.columns if c not in front]]

    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_path, index=False, compression="gzip")

    keep = df["major_metro"] & df["enough_households"]
    print(f"Wrote {out_path}  ({Path(out_path).stat().st_size / 1e6:.1f} MB)")
    print(f"  in a metro area:           {df['in_metro'].sum():>8,}")
    print(f"  in a 1M+ metro:            {df['major_metro'].sum():>8,}  ({df.loc[df['major_metro'], 'cbsa'].nunique()} metros)")
    print(f"  1M+ metro and 50+ households: {keep.sum():>5,}  <- analysis sample")
    print(f"  no transit stop within 3/4 mi (analysis sample): {df.loc[keep, 'no_stop_within_3_4mi'].mean():.0%}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    main(*sys.argv[1:])
