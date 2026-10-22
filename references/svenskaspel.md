# Direct Svenska Spel ATP feed

Fetch current prices with the bundled script, using HTTP instead of a browser:

```sh
<skill>/.venv/bin/python <skill>/scripts/svenskaspel.py
```

To preserve evidence, redirect its JSON to a dated file in the calling project.
Output contains `checked_at` (Europe/Stockholm), `source` (the exact provider
URL), and the unchanged provider payload under `response`. A failed request
exits nonzero with an error on stderr; an empty redirected file is not data.

## Extract match-winner prices

- Iterate `response.events`. Each item contains `event`, `betOffers`, and
  sometimes `liveData`. An empty events list is a valid empty offering.
- Use `event.id`, `homeName`, `awayName`, `group`, `start`, and `state`.
  `start` is normally UTC (`Z`); convert it to Europe/Stockholm for display.
  Treat start times as preliminary.
- In `betOffers`, select `criterion.englishLabel == 'Match Odds'`
  (localized `criterion.label` is `Matchodds`). Ignore set/game markets.
- Require a nonsuspended offer (`suspended` must not be true) and exactly
  two outcomes, both with `status == 'OPEN'`, named participants, and valid
  positive integer `odds`. Divide each integer price by 1000, e.g.
  `2180 / 1000 = 2.18`. Preserve `offer.id` and both `outcome.id` values.
- Match outcomes by `participant`, not their position in the array.
  Provider participant IDs are not ATP IDs. Resolve names separately in
  MariaDB and verify both player identities and the tournament edition.
- `NOT_STARTED` is prematch; `STARTED` is in progress. Keep other states
  explicit. New recommendations require verified prematch status, current
  open prices, and the calling project's time and selection constraints.
- A match disappearing from the offering is not proof of its result.
  Verify a final result separately before settlement. Live scores are
  observations, not final outcomes.

Fetch again before registering new bets. Preserve previously booked odds;
do not replace them with current prices. Check the retrieval timestamp before
describing a snapshot as current. Do not reuse a previous file after a failed
request or automatically open a browser as fallback.
