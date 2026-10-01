# OptionMetrics export for market-informed calibration

This experiment uses a listed vanilla **put** as a same-day market-implied-volatility input for simulation. It does not claim that the listed option is Asian or Bermudan.

Do not download the raw option-price panel. Download these two local CSVs and keep them out of version control.

## 1. Volatility Surface

Save as `data/raw/optionmetrics_daily.csv`.

In WRDS: **OptionMetrics → IvyDB US → Volatility Surface**.

- Select the relevant permanent `secid` values.
- Select **Equity** and **Put**.
- Use the available date range beginning at `2000-01-01`. The end date may be the vendor's latest available date; it only has to cover the historical contract starts, not each contract's later realized CRSP path.
- Set days to expiration to `365` (or a narrow `360`–`370` range if the interface requires inequalities).
- Export `secid`, `date`, `days`, `delta`, `impl_volatility`, and `cp_flag`. It is fine to export the standardized delta grid; the loader chooses the put delta closest to \(-0.50\).

## 2. Security Name History

Save as `data/raw/optionmetrics_security_map.csv`.

In WRDS: **OptionMetrics → IvyDB US → Securities → Security Name History**, export `secid`, `effect_date`, and `ticker`. If the web interface supplies a separate export for one ticker, concatenate the exports before running the project.

The loader maps each quote to the most recent ticker mapping effective on or before its date. It never uses a future ticker mapping. The raw exports remain local and are ignored by Git.
