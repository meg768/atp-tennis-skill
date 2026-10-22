# Tennis Abstract probabilities and odds

## Database calculation

Use `WIN_PROBABILITY_TA(A, B, surface)`. Prefer verified ATP IDs over free-text
names. `Hard`, `Clay`, and `Grass` select the corresponding stored surface Elo;
NULL, empty, or any other surface selects overall `elo_rank`. Check the input
surface rather than accidentally using overall Elo after a typo.

The best-of-three Elo expectation is:

```text
p(A) = 1 / (1 + 10 ** ((Elo_B - Elo_A) / 400))
p(B) = 1 - p(A)
```

This function applies no pricing margin. It returns NULL for unresolved
players, equal player identities, or missing/nonpositive selected Elo. Do not
replace NULL with a confident probability. Do not use this formula unchanged
as a best-of-five match model.

The imported TA surface Elo is already blended; do not blend it again with
overall Elo. Database Elo is stored as integers. A comparison with the public
TA decimal Elo values can differ slightly; state the source and precision.
The schema does not provide a per-player Elo refresh timestamp, so do not
claim the values are today's ratings without separate verification.

## Existing odds convention

Project TA odds include a 5% probability markup, applied once:

```text
fair odds A = 1 / p(A)
TA odds A = ROUND(1 / LEAST(0.999, GREATEST(0.001, p(A) * 1.05)), 2)
TA odds B = ROUND(1 / LEAST(0.999, GREATEST(0.001, (1-p(A)) * 1.05)), 2)
```

Multiplying by 1.05 is a pricing adjustment, not adding five percentage
points to the player's actual chance. Compare these TA prices directly
with offered bookmaker odds; do not add another 5% margin.

Read only the TA function. Skip database GPT probabilities/odds and avoid
`PLAYER_ODDS`, which also computes GPT output.

```sql
WITH probability AS (
  SELECT WIN_PROBABILITY_TA(%s, %s, %s) AS p
)
SELECT p, 1 - p AS opponent_probability,
       ROUND(1 / LEAST(0.999, GREATEST(0.001, p * 1.05)), 2) AS ta_odds,
       ROUND(1 / LEAST(0.999, GREATEST(0.001, (1-p) * 1.05)), 2) AS opponent_ta_odds
FROM probability;
```

## Comparing prices

Keep these quantities distinct:

- The price-comparison convention is
  `100 * (1/TA_odds - 1/offered_odds)`, in **percentage points (pp)**.
  Use the priced odds as shown; their existing margin remains included.
- `offered_odds/TA_odds - 1` is a relative odds difference, not that same diff.
- TA-model expected net return per unit staked is `p * offered_odds - 1`,
  using the **margin-free** probability. It is conditional on that model.

TA probability is not the assistant's independent match assessment. Keep any
independent estimate separate and explain its evidence and uncertainty. The
calling betting project determines selection rules and stores original odds;
an audit with newer or more precise ratings must not rewrite those records.

## Primary sources for verification

- [TA Elo methodology](https://www.tennisabstract.com/blog/2019/12/03/an-introduction-to-tennis-elo/)
- [TA ATP Elo ratings](https://www.tennisabstract.com/reports/atp_elo_ratings.html)

When checking the public site, record its update date and distinguish exact
rating-based calculations from rounded or simulated tournament forecasts.
