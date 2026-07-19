"""Daily missed calls via Twilio, displaying Google Voice number as caller ID.

Places NUM_CALLS calls in a row, waiting for each to finish before starting
the next. Runs from GitHub Actions. The workflow triggers at two possible UTC
times; this script only dials if it's actually 3pm in Louisiana
(America/Chicago), which makes it daylight-saving-proof. Manual runs
(workflow_dispatch) skip the time check so you can test anytime.
"""

import os
import sys
import time
from datetime import datetime
from zoneinfo import ZoneInfo

from twilio.rest import Client

TARGET_HOUR = 15        # 3pm local Louisiana time
NUM_CALLS = 5           # how many missed calls to place
RING_SECONDS = 20       # how long each call rings before giving up
GAP_SECONDS = 20        # pause between the end of one call and the next


def is_target_time() -> bool:
    now = datetime.now(ZoneInfo("America/Chicago"))
    return now.hour == TARGET_HOUR


def wait_for_call_to_finish(client: Client, call_sid: str, max_wait: int = 60) -> str:
    """Poll until the call reaches a final state; return that status."""
    final_states = {"completed", "no-answer", "busy", "failed", "canceled"}
    waited = 0
    while waited < max_wait:
        call = client.calls(call_sid).fetch()
        if call.status in final_states:
            duration = call.duration or "0"
            print(f"  -> status: {call.status}, duration: {duration}s")
            return call.status
        time.sleep(5)
        waited += 5
    print("  -> still in progress after waiting, moving on")
    return "unknown"


def main() -> None:
    manual_run = os.environ.get("GITHUB_EVENT_NAME") == "workflow_dispatch"

    if not manual_run and not is_target_time():
        # The "other" DST cron fired; not actually 3pm — exit quietly.
        print("Not 3pm in Louisiana right now, skipping this trigger.")
        sys.exit(0)

    client = Client(os.environ["TWILIO_SID"], os.environ["TWILIO_TOKEN"])

    for i in range(1, NUM_CALLS + 1):
        call = client.calls.create(
            to=os.environ["BROTHER_NUMBER"],
            from_=os.environ["GV_NUMBER"],
            # If anything answers, pause a moment then hang up.
            twiml="<Response><Pause length='1'/><Hangup/></Response>",
            timeout=RING_SECONDS,
        )
        print(f"Call {i}/{NUM_CALLS} placed: {call.sid}")
        wait_for_call_to_finish(client, call.sid)

        if i < NUM_CALLS:
            time.sleep(GAP_SECONDS)

    print("All calls done.")


if __name__ == "__main__":
    main()
