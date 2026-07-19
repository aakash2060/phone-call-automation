"""Daily missed call via Twilio, displaying Google Voice number as caller ID.

Runs from GitHub Actions. The workflow triggers at two possible UTC times;
this script only dials if it's actually 3pm in Louisiana (America/Chicago),
which makes it daylight-saving-proof. Manual runs (workflow_dispatch) skip
the time check so you can test anytime.
"""

import os
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

from twilio.rest import Client

TARGET_HOUR = 15  # 3pm local Louisiana time


def is_target_time() -> bool:
    now = datetime.now(ZoneInfo("America/Chicago"))
    return now.hour == TARGET_HOUR


def main() -> None:
    manual_run = os.environ.get("GITHUB_EVENT_NAME") == "workflow_dispatch"

    if not manual_run and not is_target_time():
        # The "other" DST cron fired; not actually 3pm — exit quietly.
        print("Not 3pm in Louisiana right now, skipping this trigger.")
        sys.exit(0)

    client = Client(os.environ["TWILIO_SID"], os.environ["TWILIO_TOKEN"])

    call = client.calls.create(
        to=os.environ["BROTHER_NUMBER"],
        from_=os.environ["GV_NUMBER"],
        # If he accidentally answers, pause a moment then hang up.
        twiml="<Response><Pause length='1'/><Hangup/></Response>",
        timeout=20,  # ring ~20 seconds, then give up => missed call
    )
    print(f"Rang him: {call.sid}")


if __name__ == "__main__":
    main()
