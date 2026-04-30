"""
LMS Enterprise – YouTube Live Service
======================================
Wraps the YouTube Data API v3 to create, manage, and end
YouTube Live broadcasts for ScheduledClass instances.

Requires per-channel OAuth2 credentials stored on the YouTubeChannel model
(access_token, refresh_token, client_id, client_secret).

All public methods raise YouTubeServiceError on failure so callers can
catch a single exception type.
"""

import logging
from datetime import datetime, timedelta, timezone as dt_timezone
from typing import Optional

from django.utils import timezone

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)

YOUTUBE_API_SERVICE = "youtube"
YOUTUBE_API_VERSION = "v3"

# Scopes required for live streaming
REQUIRED_SCOPES = [
    "https://www.googleapis.com/auth/youtube",
    "https://www.googleapis.com/auth/youtube.force-ssl",
]


class YouTubeServiceError(Exception):
    """Raised for any YouTube API error."""
    pass


class YouTubeService:
    """
    Thin wrapper around the YouTube Data API v3 for live streaming operations.

    Usage:
        svc = YouTubeService(youtube_channel_instance)
        result = svc.create_broadcast_for_class(scheduled_class_instance)
    """

    def __init__(self, channel):
        """
        :param channel: YouTubeChannel model instance with valid OAuth tokens.
        """
        self.channel = channel
        self._client = None

    # ──────────────────────────────────────────────────────────────────────────
    # Auth
    # ──────────────────────────────────────────────────────────────────────────

    def _get_credentials(self) -> Credentials:
        """Build and (if needed) refresh Google OAuth2 credentials."""
        ch = self.channel
        if not all([ch.access_token, ch.refresh_token, ch.client_id, ch.client_secret]):
            raise YouTubeServiceError(
                f"YouTubeChannel '{ch.channel_name}' is missing OAuth credentials. "
                "Please re-authorise via the admin panel."
            )

        creds = Credentials(
            token=ch.access_token,
            refresh_token=ch.refresh_token,
            client_id=ch.client_id,
            client_secret=ch.client_secret,
            token_uri="https://oauth2.googleapis.com/token",
            scopes=REQUIRED_SCOPES,
        )

        # Refresh if expired or about to expire within 5 minutes
        if creds.expired or (
            ch.token_expires_at and
            ch.token_expires_at <= timezone.now() + timedelta(minutes=5)
        ):
            try:
                creds.refresh(Request())
                # Persist refreshed tokens back to DB
                ch.access_token = creds.token
                ch.token_expires_at = creds.expiry.replace(tzinfo=dt_timezone.utc) if creds.expiry else None
                ch.save(update_fields=['access_token', 'token_expires_at', 'updated_at'])
                logger.info("Refreshed OAuth token for channel '%s'", ch.channel_name)
            except Exception as exc:
                raise YouTubeServiceError(
                    f"Failed to refresh OAuth token for channel '{ch.channel_name}': {exc}"
                ) from exc

        return creds

    def _get_client(self):
        """Return a cached authenticated YouTube API client."""
        if self._client is None:
            creds = self._get_credentials()
            self._client = build(
                YOUTUBE_API_SERVICE,
                YOUTUBE_API_VERSION,
                credentials=creds,
                cache_discovery=False,
            )
        return self._client

    # ──────────────────────────────────────────────────────────────────────────
    # Core broadcast helpers
    # ──────────────────────────────────────────────────────────────────────────

    def _create_broadcast(
        self,
        title: str,
        description: str,
        scheduled_start: datetime,
        scheduled_end: Optional[datetime],
        privacy_status: str = "unlisted",
    ) -> dict:
        """
        Create a YouTube liveBroadcast resource.
        Returns the API response dict with at minimum an 'id' key.
        """
        yt = self._get_client()

        body = {
            "snippet": {
                "title": title[:100],           # YouTube max 100 chars
                "description": description[:5000],
                "scheduledStartTime": scheduled_start.isoformat(),
            },
            "status": {
                "privacyStatus": privacy_status.lower(),
                "selfDeclaredMadeForKids": False,
            },
            "contentDetails": {
                "enableAutoStart": False,
                "enableAutoStop": False,
                "enableDvr": True,
                "recordFromStart": True,
                "enableEmbed": True,
                "monitorStream": {
                    "enableMonitorStream": True,
                    "broadcastStreamDelayMs": 0,
                },
            },
        }

        if scheduled_end:
            body["snippet"]["scheduledEndTime"] = scheduled_end.isoformat()

        try:
            response = (
                yt.liveBroadcasts()
                .insert(part="snippet,status,contentDetails", body=body)
                .execute()
            )
            logger.info("Created broadcast '%s' (id=%s)", title, response["id"])
            return response
        except HttpError as exc:
            raise YouTubeServiceError(
                f"YouTube API error creating broadcast: {exc.reason}"
            ) from exc

    def _create_stream(self, title: str) -> dict:
        """
        Create a YouTube liveStream resource (RTMP ingestion stream).
        Returns the API response dict.
        """
        yt = self._get_client()
        body = {
            "snippet": {"title": title[:100]},
            "cdn": {
                "frameRate": "variable",
                "ingestionType": "rtmp",
                "resolution": "variable",
            },
        }
        try:
            response = (
                yt.liveStreams()
                .insert(part="snippet,cdn,status", body=body)
                .execute()
            )
            logger.info("Created stream '%s' (id=%s)", title, response["id"])
            return response
        except HttpError as exc:
            raise YouTubeServiceError(
                f"YouTube API error creating stream: {exc.reason}"
            ) from exc

    def _bind_broadcast_to_stream(self, broadcast_id: str, stream_id: str) -> dict:
        """Bind a broadcast to a stream so OBS/RTMP can feed it."""
        yt = self._get_client()
        try:
            response = (
                yt.liveBroadcasts()
                .bind(part="id,contentDetails", id=broadcast_id, streamId=stream_id)
                .execute()
            )
            logger.info("Bound broadcast %s to stream %s", broadcast_id, stream_id)
            return response
        except HttpError as exc:
            raise YouTubeServiceError(
                f"YouTube API error binding broadcast to stream: {exc.reason}"
            ) from exc

    def _transition_broadcast(self, broadcast_id: str, broadcast_status: str) -> dict:
        """Transition broadcast status: 'testing' | 'live' | 'complete'."""
        yt = self._get_client()
        try:
            response = (
                yt.liveBroadcasts()
                .transition(
                    broadcastStatus=broadcast_status,
                    id=broadcast_id,
                    part="id,status",
                )
                .execute()
            )
            logger.info("Transitioned broadcast %s → %s", broadcast_id, broadcast_status)
            return response
        except HttpError as exc:
            raise YouTubeServiceError(
                f"YouTube API error transitioning broadcast to '{broadcast_status}': {exc.reason}"
            ) from exc

    # ──────────────────────────────────────────────────────────────────────────
    # High-level methods called by tasks / admin actions
    # ──────────────────────────────────────────────────────────────────────────

    def create_broadcast_for_class(self, scheduled_class) -> dict:
        """
        Creates a YouTube broadcast + stream for `scheduled_class`, binds them,
        and saves all resulting IDs/URLs back to the ScheduledClass record.

        Returns a dict with keys:
            broadcast_id, stream_id, stream_key, stream_url,
            watch_url, embed_url
        """
        from django.utils.timezone import make_aware
        import pytz

        tz = pytz.timezone(scheduled_class.class_timezone or "Asia/Kolkata")

        # Build timezone-aware datetimes
        scheduled_start = make_aware(
            datetime.combine(scheduled_class.scheduled_date, scheduled_class.start_time),
            tz,
        ).astimezone(dt_timezone.utc)

        scheduled_end = None
        if scheduled_class.end_time:
            scheduled_end = make_aware(
                datetime.combine(scheduled_class.scheduled_date, scheduled_class.end_time),
                tz,
            ).astimezone(dt_timezone.utc)

        title = f"{scheduled_class.class_code} – {scheduled_class.title}"
        description = (
            f"{scheduled_class.description or ''}\n\n"
            f"Class Code: {scheduled_class.class_code}\n"
            f"Date: {scheduled_class.scheduled_date}\n"
            f"Teacher: {scheduled_class.teacher}"
        ).strip()

        # 1. Create broadcast
        broadcast = self._create_broadcast(
            title=title,
            description=description,
            scheduled_start=scheduled_start,
            scheduled_end=scheduled_end,
            privacy_status=scheduled_class.privacy_status.lower(),
        )
        broadcast_id = broadcast["id"]
        watch_url = f"https://www.youtube.com/watch?v={broadcast_id}"
        embed_url = f"https://www.youtube.com/embed/{broadcast_id}"

        # 2. Create stream
        stream = self._create_stream(title=f"Stream – {scheduled_class.class_code}")
        stream_id = stream["id"]
        ingestion = stream.get("cdn", {}).get("ingestionInfo", {})
        stream_key = ingestion.get("streamName", "")
        stream_url = ingestion.get("ingestionAddress", "")

        # 3. Bind
        self._bind_broadcast_to_stream(broadcast_id, stream_id)

        # 4. Persist to ScheduledClass
        scheduled_class.youtube_broadcast_id = broadcast_id
        scheduled_class.youtube_stream_id    = stream_id
        scheduled_class.youtube_stream_key   = stream_key
        scheduled_class.youtube_stream_url   = stream_url
        scheduled_class.youtube_watch_url    = watch_url
        scheduled_class.youtube_embed_url    = embed_url
        scheduled_class.save(update_fields=[
            'youtube_broadcast_id', 'youtube_stream_id', 'youtube_stream_key',
            'youtube_stream_url', 'youtube_watch_url', 'youtube_embed_url',
            'updated_at',
        ])

        # 5. Track quota usage (+3 units for insert broadcast + insert stream + bind)
        self.channel.quota_used_today = (self.channel.quota_used_today or 0) + 3
        self.channel.save(update_fields=['quota_used_today', 'updated_at'])

        logger.info(
            "Broadcast ready for class %s | watch: %s | stream_key: %s",
            scheduled_class.class_code, watch_url, stream_key[:8] + "…" if stream_key else "N/A",
        )

        return {
            "broadcast_id": broadcast_id,
            "stream_id":    stream_id,
            "stream_key":   stream_key,
            "stream_url":   stream_url,
            "watch_url":    watch_url,
            "embed_url":    embed_url,
        }

    def go_live(self, scheduled_class) -> None:
        """Transition the broadcast to 'live'. Call when teacher starts the class."""
        if not scheduled_class.youtube_broadcast_id:
            raise YouTubeServiceError("No broadcast_id found on this class.")
        self._transition_broadcast(scheduled_class.youtube_broadcast_id, "live")

    def end_broadcast(self, scheduled_class) -> None:
        """Transition the broadcast to 'complete'. Call when class ends."""
        if not scheduled_class.youtube_broadcast_id:
            raise YouTubeServiceError("No broadcast_id found on this class.")
        self._transition_broadcast(scheduled_class.youtube_broadcast_id, "complete")

    def get_broadcast_status(self, broadcast_id: str) -> str:
        """Return current lifeCycleStatus of a broadcast ('created', 'ready', 'live', etc.)."""
        yt = self._get_client()
        try:
            resp = (
                yt.liveBroadcasts()
                .list(part="status", id=broadcast_id)
                .execute()
            )
            items = resp.get("items", [])
            if not items:
                return "unknown"
            return items[0]["status"]["lifeCycleStatus"]
        except HttpError as exc:
            raise YouTubeServiceError(
                f"YouTube API error fetching broadcast status: {exc.reason}"
            ) from exc

    def delete_broadcast(self, broadcast_id: str) -> None:
        """Delete a broadcast (e.g. class was cancelled)."""
        yt = self._get_client()
        try:
            yt.liveBroadcasts().delete(id=broadcast_id).execute()
            logger.info("Deleted broadcast %s", broadcast_id)
        except HttpError as exc:
            raise YouTubeServiceError(
                f"YouTube API error deleting broadcast: {exc.reason}"
            ) from exc

    # ──────────────────────────────────────────────────────────────────────────
    # Quota helpers
    # ──────────────────────────────────────────────────────────────────────────

    @staticmethod
    def reset_quota_for_all_channels():
        """
        Reset quota_used_today to 0 for all channels.
        Called daily by Celery beat task at 12:05 AM.
        """
        from classes.models import YouTubeChannel
        from django.utils import timezone as dj_tz

        count = YouTubeChannel.objects.filter(
            quota_used_today__gt=0
        ).update(
            quota_used_today=0,
            quota_reset_at=dj_tz.now(),
        )
        logger.info("Reset YouTube quota for %d channels", count)
        return count
