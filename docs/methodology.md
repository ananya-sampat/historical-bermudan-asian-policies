# Methodology

## Contract and outcome

Each eligible daily CRSP history supplies a realized one-year path of 251 prices (time zero plus 250 subsequent trading days). The path is normalized to \(S_0=100\), the strike is \(K=100\), and the arithmetic average includes time zero. Exercise is allowed every fifth trading day, for 50 dates including maturity.

For an exercise time \(\tau\), the reported policy payoff is carried to maturity with the one-year Treasury rate available at the contract start. It is compared with the payoff from holding that same hypothetical Asian put to maturity. This is an ex-post, paired realized-path difference; it is not a risk-neutral value or a traded-option return.

## Information timing

The historical path after a contract start is used only for evaluation. The policy state at date \(t\) is normalized spot and running average. Regimes use trailing one-year realized returns before the start date.

The fixed-transfer policies use the parent project's \(5\%\) rate and \(20\%\) volatility assumptions. The market-informed policies are newly trained at each start using only: (1) the last published DGS1 observation at or before that date and (2) the same-date standardized 365-day, \(-0.50\)-delta listed-put implied volatility. The latter is a vanilla-option market input, not an observed Asian-option volatility.

## Sampling and uncertainty

Starts are spaced by 250 trading days within each eligible security. Reported 95% intervals are normal-approximation intervals for the mean paired difference across the implemented contract sample. They do not remove dependence across dates, selection of the stock universe, or model-training uncertainty.

Synthetic data exists only to exercise the pipeline and tests. Every synthetic output is labeled as such.
