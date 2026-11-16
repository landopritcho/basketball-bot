import json
import logging
import time
from datetime import datetime
from pathlib import Path
from urllib.request import Request, urlopen

SCHEDULE_URL = (
    "https://site.api.espn.com/apis/site/v2/sports/"
    "basketball/mens-college-basketball/scoreboard"
)
POLL_INTERVAL_SECONDS = 300

def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )
    capture_date = datetime.now().date()
    output_directory = (
        Path(__file__).resolve().parent.parent / "schedule_snapshots"
    )
    output_directory.mkdir(parents=True, exist_ok=True)

    url = (
        f"{SCHEDULE_URL}?dates={capture_date:%Y%m%d}"
        "&groups=50&limit=1000"
    )
    next_poll = time.monotonic()
    logging.info("Capturing %s into %s", url, output_directory)

    while datetime.now().date() == capture_date:
        remaining = next_poll - time.monotonic()
        if remaining > 0:
            time.sleep(min(remaining, 1.0))
            continue

        next_poll = time.monotonic() + POLL_INTERVAL_SECONDS
        captured_at = datetime.now().astimezone()
        request = Request(url, headers={"User-Agent": ""})

        try:
            with urlopen(request, timeout=20) as response:
                body = response.read()

            json.loads(body)

            if datetime.now().date() != capture_date:
                break

            filename = f"schedule_{captured_at:%Y%m%dT%H%M%S.%f%z}.json"
            destination = output_directory / filename
            destination.write_bytes(body)
            logging.info("Saved %s (%d bytes)", destination, len(body))
        except (OSError, ValueError):
            logging.exception("Snapshot failed; retrying at the next poll")

    logging.info("System date changed; stopping")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logging.info("Stopped manually")
