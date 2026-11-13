"""Pull Census ACS 2014-2018 5-year block-group data and save a table that joins to the SLD on `geoid`.

Run from the repo root (after build_sld.py):
    python src/build_acs.py

Requires a free Census API key (required for all requests since May 2026).
Sign up at https://api.census.gov/data/key_signup.html with a .edu/.com/.org email,
click the activation link in the email (activation can take a few minutes), then run:
    export CENSUS_API_KEY=your_key_here      (Mac / Linux; lasts for this Terminal window)
Never commit the key to the repo.

Mac note: if you get "CERTIFICATE_VERIFY_FAILED", run once:
    "/Applications/Python 3.x/Install Certificates.command"   (use your Python version)

Writes:
    data/processed/acs_blockgroups.csv.gz

Why these tables:
  - B19013 (median household income): car ownership rises with income, and income is
    correlated with density, transit, and mixed use. We use it as a control so we don't
    credit a built-environment feature for what is really an income difference.
  - B08301 (means of transportation to work): a second, behavior-based measure of car
    dependence (do people actually drive to work?) to check the car-ownership results.

Why ACS 2014-2018: it is the same ACS release the SLD used for its car-ownership columns,
so both tables describe the same households in the same years and the same 2010-vintage
block-group boundaries. The join on `geoid` is therefore one-to-one.
"""

import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd

API = "https://api.census.gov/data/2018/acs/acs5"
SLD_PATH = "data/processed/sld_blockgroups.csv.gz"
OUT_PATH = "data/processed/acs_blockgroups.csv.gz"

# ACS variable -> our column name.  E = estimate, M = margin of error (90% level).
VARIABLES = {
    "B19013_001E": "median_hh_income",
    "B19013_001M": "median_hh_income_moe",
    "B08301_001E": "workers",            # workers 16+ (denominator for commute shares)
    "B08301_003E": "n_drove_alone",
    "B08301_004E": "n_carpool",
    "B08301_010E": "n_transit",          # public transportation, excluding taxicab
    "B08301_018E": "n_bike",
    "B08301_019E": "n_walk",
    "B08301_021E": "n_work_from_home",
}

# The Census API uses large negative numbers as codes for "not available"
# (e.g. -666666666 = median could not be computed because too few households).
# Any value below this threshold is treated as missing.
CENSUS_NULL_BELOW = -100_000_000


def get_json(params: dict, retries: int = 3) -> list:
    """Call the Census API and return the parsed JSON (a list of rows, first row = header)."""
    key = os.environ.get("CENSUS_API_KEY")
    if not key:
        raise SystemExit("No Census API key found. Run:  export CENSUS_API_KEY=your_key_here  (see top of this file)")
    params = {**params, "key": key}
    # quote_via=quote encodes spaces as %20 (the form the Census API documents)
    url = API + "?" + urllib.parse.urlencode(params, safe=":*,", quote_via=urllib.parse.quote)
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(url, timeout=120) as resp:
                # An invalid or not-yet-activated key gets redirected to an HTML page instead of data.
                if "invalid_key" in resp.geturl():
                    raise SystemExit("Census API rejected the key (invalid or not activated yet). "
                                     "Click the activation link in the signup email, wait a few minutes, try again.")
                return json.loads(resp.read().decode("utf-8"))
        except (urllib.error.URLError, json.JSONDecodeError) as err:
            if attempt == retries - 1:
                raise RuntimeError(f"Census API request failed: {url.replace(key, 'KEY')}\n{err}") from err
            time.sleep(2 * (attempt + 1))


def rows_to_frame(rows: list) -> pd.DataFrame:
    """Turn the API's list-of-lists into a DataFrame with a 12-digit geoid."""
    df = pd.DataFrame(rows[1:], columns=rows[0])
    df["geoid"] = df["state"] + df["county"] + df["tract"] + df["block group"]
    return df[["geoid"] + list(VARIABLES)]


def fetch_state(state: str, counties: list) -> pd.DataFrame:
    """All block groups in one state's counties of interest.

    First try one request for the whole state. If the API refuses the wildcard,
    fall back to one request per county (slower, but always supported).
    """
    base = {"get": ",".join(VARIABLES), "for": "block group:*"}
    try:
        rows = get_json({**base, "in": f"state:{state} county:* tract:*"})
        df = rows_to_frame(rows)
        return df[df["geoid"].str[2:5].isin(counties)]
    except RuntimeError:
        parts = []
        for county in counties:
            rows = get_json({**base, "in": f"state:{state} county:{county} tract:*"})
            parts.append(rows_to_frame(rows))
        return pd.concat(parts, ignore_index=True)


def clean(raw: pd.DataFrame) -> pd.DataFrame:
    """Convert to numbers, turn Census null codes into NaN, and compute commute shares."""
    df = raw.rename(columns=VARIABLES)
    num = list(VARIABLES.values())
    df[num] = df[num].apply(pd.to_numeric, errors="coerce")
    df[num] = df[num].mask(df[num] < CENSUS_NULL_BELOW)

    # ACS top-codes median income at $250,001. Flag it so we know those values are a floor.
    df["income_topcoded"] = df["median_hh_income"] >= 250_001

    # Commute shares (0-100) out of ALL workers, the standard Census definition.
    # Work-from-home is kept as its own share rather than dropped, so the shares add up.
    workers = df["workers"].where(df["workers"] > 0)
    for mode in ["drove_alone", "carpool", "transit", "bike", "walk", "work_from_home"]:
        df[f"pct_{mode}"] = (df[f"n_{mode}"] / workers * 100).round(2)

    # Relative margin of error for income: how noisy is each block group's estimate?
    # (MOE is at the 90% level. Useful later for the uncertainty discussion.)
    df["income_rel_moe"] = (df["median_hh_income_moe"] / df["median_hh_income"]).round(3)
    return df


def main(sld_path: str = SLD_PATH, out_path: str = OUT_PATH) -> None:
    # Only request the states and counties that are in our analysis sample (1M+ metros, 50+ HH).
    sld = pd.read_csv(sld_path, dtype={"geoid": str, "cbsa": str},
                      usecols=["geoid", "major_metro", "enough_households"])
    sample = sld[sld["major_metro"] & sld["enough_households"]]
    counties_by_state = (
        sample.assign(state=sample["geoid"].str[:2], county=sample["geoid"].str[2:5])
        .groupby("state")["county"].unique()
    )
    print(f"Requesting ACS for {len(counties_by_state)} states, "
          f"{sum(len(c) for c in counties_by_state)} counties")

    parts = []
    for state, counties in counties_by_state.items():
        part = fetch_state(state, list(counties))
        print(f"  state {state}: {len(part):,} block groups")
        parts.append(part)
    acs = clean(pd.concat(parts, ignore_index=True))

    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    acs.to_csv(out_path, index=False, compression="gzip")

    # Join check: every block group in the analysis sample should find an ACS match.
    matched = sample["geoid"].isin(acs["geoid"])
    print(f"Wrote {out_path}  ({Path(out_path).stat().st_size / 1e6:.1f} MB, {len(acs):,} rows)")
    print(f"  analysis-sample block groups matched: {matched.mean():.1%}")
    in_sample = acs[acs["geoid"].isin(sample["geoid"])]
    print(f"  missing median income (in sample):    {in_sample['median_hh_income'].isna().mean():.1%}")
    print(f"  top-coded income (in sample):         {in_sample['income_topcoded'].mean():.1%}")


if __name__ == "__main__":
    main(*sys.argv[1:])
