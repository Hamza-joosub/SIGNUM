
## Notation

```
t       = current trading day
n       = window length in trading days (5, 21, 63, 126, 252)
P(t)    = closing price at time t
V(t)    = volume at time t
i       = ticker index
U       = full universe of tickers
```

---

## Layer 1 — Momentum

**Raw return over window:**

$$r_i = \frac{P_i(t) - P_i(t-n)}{P_i(t-n)} \times 100$$

**Normalised against instrument's own history:**

$$M_i = \frac{2(r_i - \min(r_i)) }{\max(r_i) - \min(r_i)} - 1 \quad \in [-1, +1]$$

Where $\min$ and $\max$ are taken over all historical rolling $n$-day returns for instrument $i$. This means a return that is historically large for this instrument scores closer to +1, even if the raw percentage is modest.

---

## Layer 2 — Volume Conviction

**30-day trailing average volume, excluding today:**

$$\bar{V}_i(t) = \frac{1}{30} \sum_{k=1}^{30} V_i(t-k)$$

**Volume ratio:**

$$\rho_i = \frac{V_i(t)}{\bar{V}_i(t)}$$

**Log-scaled and clipped:**

$$V_i^{raw} = \ln(\max(\rho_i, 0.01))$$

$$V_i^{norm} = \text{clip}\left(\frac{V_i^{raw}}{\ln(3)}, -1, +1\right)$$

The $\ln(3)$ denominator means a volume ratio of exactly 3x average scores +1.0. Below average volume scores negative. Log scaling prevents a 10x spike dominating a 3x spike by a factor of 10.

**Reliability discount:**

$$V_i = V_i^{norm} \times \delta_i$$

Where $\delta_i \in [0.1, 1.0]$ is a per-instrument constant reflecting how meaningful ETF volume is as a proxy for true capital flow.

---

## Layer 3 — Relative Pressure

**Universe average return:**

$$\bar{r} = \frac{1}{|U|} \sum_{j \in U} r_j$$

**Relative return:**

$$\Delta_i = r_i - \bar{r}$$

**Normalised across universe:**

$$R_i = \frac{2(\Delta_i - \Delta_{min})}{\Delta_{max} - \Delta_{min}} - 1 \quad \in [-1, +1]$$

Where $\Delta_{min} = \min_j(r_j) - \bar{r}$ and $\Delta_{max} = \max_j(r_j) - \bar{r}$.

This means the best relative performer always scores +1 and the worst always scores -1, regardless of absolute return levels. It purely captures rotation.

---

## Layer 4 — Positioning Stretch

**Net speculative position:**

$$N_i(t) = \text{Lev\_Long}_i(t) - \text{Lev\_Short}_i(t)$$

**52-week trailing mean and std, excluding current week:**

$$\mu_i = \frac{1}{52} \sum_{k=1}^{52} N_i(t-k)$$

$$\sigma_i = \sqrt{\frac{1}{51} \sum_{k=1}^{52} (N_i(t-k) - \mu_i)^2}$$

**Z-score:**

$$z_i = \frac{N_i(t) - \mu_i}{\sigma_i}$$

---

## Positioning Modifier Decision Rule

First determine if positioning is in the same direction as the raw pressure signal:

$$\text{same\_direction} = \begin{cases} \text{True} & \text{if } z_i > 0 \text{ and direction} = \text{inflow} \\ \text{True} & \text{if } z_i < 0 \text{ and direction} = \text{outflow} \\ \text{False} & \text{otherwise} \end{cases}$$

Then apply:

$$\lambda_i = \begin{cases} 1.0 & \text{if } z_i = \text{None} \quad \text{(no COT data)} \\ 1.0, \text{ contrarian=True} & \text{if same\_direction} = \text{False} \\ 1.0 & \text{if same\_direction and } |z_i| < 1.5 \\ 0.75 & \text{if same\_direction and } 1.5 \leq |z_i| < 2.0 \\ 0.50 & \text{if same\_direction and } |z_i| \geq 2.0 \end{cases}$$

---

## Layer Weights

Per-instrument weights $w_i^{(m)}, w_i^{(v)}, w_i^{(r)}$ where superscripts denote momentum, volume, relative.

**Default (most instruments):**

$$w^{(m)} = 0.30, \quad w^{(v)} = 0.25, \quad w^{(r)} = 0.30$$

**Overrides for thin/OTC instruments (GLD, TLT, BIL, SHV, UUP, FXY):**

$$w^{(m)} = 0.40\text{–}0.45, \quad w^{(v)} = 0.00\text{–}0.05, \quad w^{(r)} = 0.45$$

Note: weights sum to 0.85 by design — the remaining 0.15 is reserved for positioning but applied as a modifier, not an addend.

---

## Composite Raw Score

$$S_i^{raw} = \left( w_i^{(m)} \cdot M_i + w_i^{(v)} \cdot V_i + w_i^{(r)} \cdot R_i \right) \times \lambda_i$$

Scaled to $[-10, +10]$:

$$S_i = S_i^{raw} \times 10$$

Theoretical maximum before rescaling: $(0.30 + 0.25 + 0.30) \times 10 = 8.5$

---

## Universe Rescaling

After computing $S_i$ for all $i \in U$:

$$S_i^{final} = \frac{S_i}{\max_{j \in U}|S_j|} \times 10$$

This anchors the strongest signal at $\pm 10$ and preserves relative magnitudes across the universe.

---

## Confidence Decision Rule

Applied after rescaling:

$$\text{confidence}_i = \begin{cases} \text{HIGH}   & \text{if } |S_i^{final}| \geq 6.0 \\ \text{MEDIUM} & \text{if } 3.0 \leq |S_i^{final}| < 6.0 \\ \text{LOW}     & \text{if } |S_i^{final}| < 3.0 \end{cases}$$

---

## Direction

$$\text{direction}_i = \begin{cases} \text{inflow}  & \text{if } S_i^{final} > 0 \\ \text{outflow} & \text{if } S_i^{final} < 0 \end{cases}$$

---

## Summary of the full pipeline

$$P_i(t) \xrightarrow{\text{L1}} M_i \xrightarrow{} \quad \text{weighted sum} \xrightarrow{\times \lambda_i} S_i^{raw} \xrightarrow{\times 10} S_i \xrightarrow{\text{rescale}} S_i^{final}$$

$$V_i(t) \xrightarrow{\text{L2}} V_i \xrightarrow{}$$

$$\{r_j\}_{j \in U} \xrightarrow{\text{L3}} R_i \xrightarrow{}$$

$$N_i(t) \xrightarrow{\text{L4}} z_i \xrightarrow{} \lambda_i$$
