import time
import requests
import asyncio
from plyer import notification

from upchups import (
    initialize_database,
    get_google_credentials,
    sync_tasks_to_db,
    show_todays_tasks_from_db
)


def has_internet():
    try:
        requests.get("https://www.google.com", timeout=3)
        return True
    except:
        return False


async def monitor_and_notify():
    print("🔁 Upchups background sync is watching for internet...")

    while True:
        # Wait until internet is back
        while not has_internet():
            await asyncio.sleep(10)

        try:
            print("🌐 Internet is back! Syncing with Google Tasks...")
            creds = get_google_credentials()
            sync_tasks_to_db(creds)

            # Get today's summary
            summary = show_todays_tasks_from_db()

            # Send desktop notification
            if summary is not None:
                notification.notify(
                    title="Upchups Sync Complete",
                    message=summary,
                    timeout=10,  # seconds
                ) # type: ignore
            else:
                print("No summary to notify.")

            print("🔔 Notification sent.")

        except Exception as e:
            print("❌ Error during sync or notify:", e)

        await asyncio.sleep(3600)  # Wait 1 hour before next check

if __name__ == "__main__":
    initialize_database()
    asyncio.run(monitor_and_notify())
