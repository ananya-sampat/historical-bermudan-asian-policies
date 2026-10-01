# WRDS download instructions

This repository expects a **local, licensed** CRSP daily-stock export at `data/raw/crsp_daily.csv`. Do not commit or upload that file.

In WRDS, request a daily CRSP stock file with at least `PERMNO`, `date`, `PRC`, and `RET`. Include `DLRET`, `CFACPR`, `SHRCD`, and `EXCHCD` when available. Export CSV with one row per security-date and rename columns to lower case, or adapt `src/crsp_loader.py` once in a documented mapping step.

`PERMNO` is used instead of a ticker because tickers change. `PRC` may be negative in CRSP; the loader uses its absolute value. `DLRET` is retained when present so delisting observations are not silently ignored. `CFACPR` enables split adjustment.

## Risk-free rate for rolling calibration

The fixed-policy transfer uses its deliberately fixed 5% simulation assumption.
The rolling-calibration experiment instead requires a local copy of FRED's
daily `DGS1` series: **Market Yield on U.S. Treasury Securities at 1-Year
Constant Maturity**. Download the CSV from
https://fred.stlouisfed.org/graph/fredgraph.csv?id=DGS1 and save it as
`data/raw/dgs1.csv`. The file has `DATE` and `DGS1` columns, with DGS1 quoted
in percent. The loader uses only the last observation published on or before
each contract start date; it never looks ahead. It treats this one-year
Treasury yield as a rate proxy and holds it constant over the remaining
contract period.

The raw export, derived licensed rows, and any non-permitted extracts remain outside public GitHub.
## Your CRSP CIZ export

The CRSP Stock Version 2 (CIZ) daily export is supported directly.  Its common
column names are `PERMNO`, `DlyCalDt`, `DlyPrc`, and `DlyRet`; the loader maps
them automatically.  It forms normalized paths from cumulative `DlyRet` so
that stock splits do not create artificial price jumps.  Because CRSP return
fields can reflect distributions as well as price changes, results should be
described as hypothetical-contract results on CRSP realized-return paths.
