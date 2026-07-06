import httpx
from app.config import settings

ONESIGNAL_URL = "https://onesignal.com/api/v1/notifications"

HEADERS = {
    "Content-Type": "application/json",
    "Authorization": f"Basic {settings.ONESIGNAL_API_KEY}",
}


async def send_push(
    player_ids: list[str],
    title: str,
    message: str,
    data: dict = {},
) -> dict:
    """
    Sends a push notification to a list of OneSignal player IDs.
    `data` is a custom payload Flutter can read in the notification handler.
    """
    if not player_ids:
        return {"skipped": "no player_ids provided"}

    payload = {
        "app_id": settings.ONESIGNAL_APP_ID,
        "include_player_ids": player_ids,
        "headings": {"en": title},
        "contents": {"en": message},
        "data": data,
        "ios_badgeType": "Increase",
        "ios_badgeCount": 1,
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(ONESIGNAL_URL, json=payload, headers=HEADERS)
        response.raise_for_status()
        return response.json()


async def send_push_to_segments(
    segments: list[str],
    title: str,
    message: str,
    data: dict = {},
) -> dict:
    """
    Broadcasts to a OneSignal segment (e.g. 'Educators', 'All').
    Segments are configured in the OneSignal dashboard.
    """
    payload = {
        "app_id": settings.ONESIGNAL_APP_ID,
        "included_segments": segments,
        "headings": {"en": title},
        "contents": {"en": message},
        "data": data,
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(ONESIGNAL_URL, json=payload, headers=HEADERS)
        response.raise_for_status()
        return response.json()
