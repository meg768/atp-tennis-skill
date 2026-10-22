---
name: atp-tennis
description: Query Magnus's ATP MariaDB database for players, rankings, match history, statistics, and Tennis Abstract Elo probabilities and odds. Use across the tennis projects when an answer needs this database or its schema.
---

# ATP tennis

Use the bundled `scripts/database.py` to read the ATP database directly. Resolve
paths relative to this skill's directory, not the calling project's directory.
The script resolves its own directory even when the skill is symlinked.

## Connection and queries

Use `<skill>/.venv/bin/python` and `<skill>/scripts/database.py`, replacing
`<skill>` with the discovered skill directory's absolute path. Initial setup:

```sh
python3 -m venv <skill>/.venv
<skill>/.venv/bin/python -m pip install -r <skill>/requirements.txt
```

Read credentials from `<skill>/.env`. `.env.example` lists the required keys.
An explicit `--env-file /absolute/path/to/.env` overrides `ATP_TENNIS_ENV_FILE`,
which overrides the default file. Do not guess another project's credentials
when the selected file is missing. Never print credentials or include `.env`
in Git, reports, or examples.

SQL can come from a file or standard input; output is JSON containing result
sets with `rows` and `rowcount`:

```sh
echo 'SELECT 1 AS connection_ok;' | <skill>/.venv/bin/python <skill>/scripts/database.py
<skill>/.venv/bin/python <skill>/scripts/database.py /absolute/path/query.sql
echo 'SELECT id, name, rank FROM players WHERE id = %s;' | <skill>/.venv/bin/python <skill>/scripts/database.py --params '["S0AG"]'
```

For programmatic use, import `scripts/database.py` from the skill and call
`execute(sql, params=None, env_file=None)`. Bind values with `%s` parameters;
do not interpolate player names into SQL. The tool accepts one statement
beginning with SELECT, WITH, SHOW, DESCRIBE, DESC, or EXPLAIN. It uses a read-only
MariaDB transaction and always rolls back and closes the connection. CALL and
database mutations are outside this tool's scope. This skill does not grant
permission to change data or schema; follow the user's authorization. For a
database-level security boundary, use an account with read-only grants.

## Working with tennis data

- Read [references/schema.md](references/schema.md) for tables, joins,
  identity resolution, match statuses, and time limitations. Check live
  metadata when the required field is not documented or has changed.
- Read [references/ta-odds.md](references/ta-odds.md) for TA probabilities,
  the existing 5% pricing margin, precision, and comparison formulas.
- Resolve both players to ATP IDs and confirm their names before match
  analysis. `PLAYER_LOOKUP` returns one best match; inspect ambiguous names
  rather than trusting that choice automatically.
- Distinguish ATP ranking positions from Elo rating values. State date,
  surface, tournament levels, qualification scope, and whether aborted
  matches or walkovers enter a statistic. Database history may lag live play.
- Do not use `tennis.egelberg.se`, including as a fallback or proxy. Fetch
  fresh external information from ATP, organizers, Tennis Abstract, or the
  relevant odds provider when the task requires it. Verify access and cite
  the actual source; this skill itself provides database access only.
- Keep betting portfolios, stake sizes, selection windows, and `ping`
  behavior in the calling project. Consult that project's instructions.
  This shared skill neither places bets nor registers recommendations.
