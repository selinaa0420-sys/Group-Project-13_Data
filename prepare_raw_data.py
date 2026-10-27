"""
Role D (Liao Juncheng) - one-off script that turns the original downloads into
the small CSV files we host on GitHub. It is NOT part of the Colab notebook;
the notebook reads the CSVs it writes. Kept here so every number can be traced
back to its original source.

Original sources (downloaded 2026-10-26):
  - Penn World Table 11.0, Feenstra, Inklaar & Timmer, GGDC
      https://www.rug.nl/ggdc/productivity/pwt/  (Excel: https://dataverse.nl/api/access/datafile/554105)
  - World Bank WDI API, https://api.worldbank.org/v2/
      SE.SEC.ENRR      School enrollment, secondary (% gross)
      SP.POP.1519.MA   Population ages 15-19, male
      SP.POP.1519.FE   Population ages 15-19, female
      SP.POP.1564.TO   Population ages 15-64, total
      NY.GDP.PETR.RT.ZS Oil rents (% of GDP)
  - MRW (1992) appendix data, as distributed by Bruce Hansen
      https://users.ssc.wisc.edu/~bhansen/econometrics/MRW1992.txt

Usage: python prepare_raw_data.py <raw_download_dir> <output_data_dir>
"""
import json
import sys
from pathlib import Path

import pandas as pd

raw, out = Path(sys.argv[1]), Path(sys.argv[2])
out.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------- PWT 11.0
# Keep only the variables we map to MRW (plus a few alternatives E may want).
pwt_cols = ["countrycode", "country", "year", "rgdpo", "rgdpe", "pop", "emp", "hc", "csh_i"]
pwt = pd.read_excel(raw / "pwt110.xlsx", sheet_name="Data", usecols=pwt_cols)
# Keep only the years of our two estimation windows (1960-1985 and 1990-2019).
pwt = pwt[pwt.year.between(1960, 1985) | pwt.year.between(1990, 2019)]
pwt.to_csv(out / "pwt11.0.csv", index=False)
print("PWT subset:", pwt.shape, "countries:", pwt.countrycode.nunique())

# ---------------------------------------------------------------- WDI
# The API returns regional aggregates too; keep real countries only.
meta = json.load(open(raw / "wdi_countries.json", encoding="utf-8"))[1]
countries = {c["id"] for c in meta if c["region"]["value"] != "Aggregates"}

def load_wdi(code, name):
    rows = json.load(open(raw / f"wdi_{code}.json", encoding="utf-8"))[1]
    df = pd.DataFrame(
        {"iso3": r["countryiso3code"], "year": int(r["date"]), name: r["value"]} for r in rows
    )
    return df[df.iso3.isin(countries)]

wdi = load_wdi("SE.SEC.ENRR", "sec_enrr")
for code, name in [("SP.POP.1519.MA", "pop1519_m"), ("SP.POP.1519.FE", "pop1519_f"),
                   ("SP.POP.1564.TO", "pop1564"), ("NY.GDP.PETR.RT.ZS", "oil_rents")]:
    wdi = wdi.merge(load_wdi(code, name), on=["iso3", "year"], how="outer")
wdi = wdi.sort_values(["iso3", "year"])
wdi.to_csv(out / "wdi.csv", index=False)
print("WDI panel:", wdi.shape, "countries:", wdi.iso3.nunique())

# ---------------------------------------------------------------- MRW + ISO3
# MRW uses its own country spellings; attach ISO3 codes (same order as the file)
# so the original data can be matched to PWT/WDI.
iso3 = """DZA AGO BEN BWA BFA BDI CMR CAF TCD COG EGY ETH GAB GMB GHA GIN CIV KEN LSO LBR MDG
MWI MLI MRT MUS MAR MOZ NER NGA RWA SEN SLE SOM ZAF SDN SWZ TZA TGO TUN UGA COD ZMB ZWE
AFG BHR BGD MMR HKG IND IRN IRQ ISR JPN JOR KOR KWT MYS NPL OMN PAK PHL SAU SGP LKA SYR
TWN THA ARE YEM AUT BEL CYP DNK FIN FRA DEU GRC ISL IRL ITA LUX MLT NLD NOR PRT ESP SWE
CHE TUR GBR BRB CAN CRI DOM SLV GTM HTI HND JAM MEX NIC PAN TTO USA ARG BOL BRA CHL COL
ECU GUY PRY PER SUR URY VEN AUS FJI IDN NZL PNG""".split()
mrw = pd.read_csv(raw / "MRW1992.txt", sep="\t", na_values="NA")
assert len(mrw) == len(iso3) == 121
mrw.insert(1, "iso3", iso3)
mrw.to_csv(out / "mrw1992_with_iso3.csv", index=False)
print("MRW:", mrw.shape, mrw[["N", "I", "O"]].sum().to_dict())
