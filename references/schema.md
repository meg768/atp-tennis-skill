# ATP database schema

Verified against the live MariaDB schema on 2026-10-22. This is an analysis
guide, not a schema dump or migration. Inspect `SHOW TABLES`, `SHOW COLUMNS`,
or `information_schema` for fields not covered here.

## Tables and relations

| Object | Key and purpose |
| --- | --- |
| `players` | `id`: ATP player ID such as `S0AG`; current player attributes |
| `events` | `id`: tournament edition, such as `2026-9410` |
| `matches` | `id`: match identifier; links to one event and two players |
| `flatly` | Joined view of matches, events, and both player names |
| `log` | Import/application messages; inspect columns when needed |
| `settings` | Application configuration; query only relevant keys and avoid exposing secrets |

Join `matches.event = events.id`, `matches.winner = players.id`, and
`matches.loser = players.id`. The two player joins need separate aliases.
Confirm player identities using IDs, names, and country when relevant.

### Players

- Identity: `id`, `name`, `country`, `birthdate`, `age`, `pro`, `active`,
  `height`, `weight`, `coach`, `url`, `wikipedia`.
- Ranking: `rank`, `points`, `highest_rank`, `highest_rank_date`.
  Select ranked players using `rank IS NOT NULL` and sort by `rank, id`.
  Do not require `points`: a player can have a rank without imported points.
- Career: `career_wins`, `career_losses`, `career_titles`, `career_prize`.
- Year to date: `ytd_wins`, `ytd_losses`, `ytd_titles`, `ytd_prize`.
- ATP ratings: `serve_rating`, `return_rating`, `pressure_rating`.
- Tennis Abstract Elo: `elo_rank`, `elo_rank_hard`, `elo_rank_clay`,
  `elo_rank_grass`. These are rating **values**, not ranking positions.
  All four are currently `INT(11)`; original decimal precision is lost.
- Other surface attributes: `hard_factor`, `clay_factor`, `grass_factor`.
  Do not treat these as Elo or win probabilities.

Player fields describe the currently imported snapshot. Use `birthdate` for
age on a historical date. Current `rank` is not historical match ranking;
use `matches.winner_rank`/`loser_rank` for the stored match context.

### Events

`id`, `date`, `name`, `location`, `type`, `surface`, `url`.
`date` is the **tournament start date**, not the date a match was played.
Surface values include `Hard`, `Clay`, and `Grass`. Hard does not distinguish
indoor from outdoor. Inspect actual `type` values before filtering levels.

### Matches

`id`, `event`, `round`, `winner`, `loser`, `winner_rank`, `loser_rank`,
`score`, `status`, `duration`.

- Status is `Completed`, `Aborted`, `Walkover`, or `Unknown` (also nullable).
  For fully played match statistics default to `Completed`. Include aborted
  matches only when the requested metric calls for them, and label that choice.
  Walkovers are not played wins for playing-performance statistics.
- `score` is oriented from the stored winner's side. Example:
  `7-6(5) 3-6 6-3`. Preserve tiebreaks and status when interpreting it.
- Rounds include `F`, `SF`, `QF`, `R16`, `R32`, `R64`, `R128`, and
  qualifying rounds such as `Q1`, `Q2`, `Q3`. Do not sort round strings
  alphabetically to infer match chronology.
- There is no per-match date or scheduled start column. Ordering by event
  date and round only approximates recent form. Do not claim an exact
  match date, live status, or future start time from this schema.
- A missing record is not proof that a match is unplayed or cancelled.
  Imports can lag; use verified external sources for live state.

### Joined view

`flatly` exposes `id`, `event_date`, `event_id`, `event_name`,
`event_location`, `event_type`, `event_surface`, `round`, `winner`, `loser`,
`winner_id`, `winner_rank`, `loser_id`, `loser_rank`, `score`, `status`,
`duration`. Here `winner` and `loser` are **names**; the `_id` fields are IDs.

## Useful functions

`PLAYER_LOOKUP(searchTerm)` returns one best matching ATP ID or NULL. Its
matching favors exact ID, exact name, surname, prefix, then substring, with
activity and ranking tie-breakers. For ambiguous names inspect candidate
rows instead of treating its first match as certain.

`WIN_PROBABILITY_TA(playerID, opponentID, surface)` returns a marginal-free
win probability or NULL. See [ta-odds.md](ta-odds.md).

Other available functions include `NUMBER_OF_GAMES`, `NUMBER_OF_SETS`,
`NUMBER_OF_TIE_BREAKS`, and `PLAYER_RANK_AT_DATE`. Inspect their definitions
and parameters before relying on behavior not verified for the task.

## Example: recent completed matches

Bind the same player ID twice. This example includes all imported tournament
levels and main-draw/qualifying rounds; add explicit filters when needed.

```sql
SELECT m.id, e.date AS event_start_date, e.id AS event_id,
       e.name AS event_name, e.type, e.surface, m.round,
       m.winner, w.name AS winner_name, m.loser, l.name AS loser_name,
       m.score, m.status
FROM matches m
JOIN events e ON e.id = m.event
LEFT JOIN players w ON w.id = m.winner
LEFT JOIN players l ON l.id = m.loser
WHERE (m.winner = %s OR m.loser = %s) AND m.status = 'Completed'
ORDER BY e.date DESC,
  CASE m.round WHEN 'F' THEN 10 WHEN 'SF' THEN 9 WHEN 'QF' THEN 8
    WHEN 'R16' THEN 7 WHEN 'R32' THEN 6 WHEN 'R64' THEN 5
    WHEN 'R128' THEN 4 WHEN 'Q3' THEN 3 WHEN 'Q2' THEN 2
    WHEN 'Q1' THEN 1 ELSE 0 END DESC,
  m.id DESC
LIMIT 10;
```
