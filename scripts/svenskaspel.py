"""Fetch Svenska Spel's current ATP offering directly, without a browser."""

import argparse
from datetime import datetime
import json
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo


SOURCE = (
    "https://eu1.offering-api.kambicdn.com/offering/v2018/svenskaspel/"
    "listView/tennis/atp/all/all/matches.json"
    "?channel_id=1&client_id=200&lang=sv_SE&market=SE"
    "&useCombined=true&useCombinedLive=true"
)


class OddsError(Exception):
    """A failed request or an unusable offering response."""


def fetch():
    """Return source, retrieval time, and the original provider response.

    Preserve all markets and states for analysis; callers must select open
    match-winner markets and verify identities before recommending a bet.
    """
    request = Request(SOURCE, headers={"Accept": "application/json"})
    try:
        with urlopen(request, timeout=20) as response:
            payload = json.load(response)
    except HTTPError as error:
        raise OddsError(f"Svenska Spel feed returned HTTP {error.code}.") from None
    except (URLError, OSError):
        raise OddsError("Unable to reach Svenska Spel feed.") from None
    except (ValueError, UnicodeError):
        raise OddsError("Svenska Spel feed returned invalid JSON.") from None

    if (not isinstance(payload, dict) or not isinstance(payload.get("events"), list)
            or any(not isinstance(item, dict)
                   or not isinstance(item.get("event"), dict)
                   or "id" not in item["event"] for item in payload["events"])):
        raise OddsError("Svenska Spel feed returned an unexpected data structure.")

    return {
        "checked_at": datetime.now(ZoneInfo("Europe/Stockholm")).isoformat(),
        "source": SOURCE,
        "response": payload,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    try:
        result = fetch()
    except OddsError as error:
        print(str(error), file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
