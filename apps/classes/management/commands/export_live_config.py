import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from classes.models import YouTubeChannel
from system_config.models import ClassLinkConfig, IntegrationConfig


def _serialize(value):
    """Make Django/DB values JSON-serializable (UUIDs, Decimals, etc.)."""
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    # UUID, Decimal, and other simple objects → string
    try:
        return str(value)
    except Exception:
        return repr(value)


class Command(BaseCommand):
    """Export Live Classes & YouTube configuration to a JSON file.

    Includes:
      - YouTubeChannel records
      - ClassLinkConfig entries for live platforms (YOUTUBE/ZOOM/GOOGLE_MEET/MS_TEAMS/CUSTOM)
      - IntegrationConfig entries for integration_type='YOUTUBE'
    """

    help = "Export Live Classes & YouTube configuration to JSON"

    def add_arguments(self, parser):
        parser.add_argument(
            "output",
            nargs="?",
            default="export/live_config.json",
            help="Output JSON file path (default: export/live_config.json)",
        )

    def handle(self, *args, **options):
        output_path = Path(options["output"]).resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)

        self.stdout.write(self.style.MIGRATE_HEADING("Collecting Live Classes & YouTube configuration..."))

        yt_channels = []
        for obj in YouTubeChannel.objects.all():
            yt_channels.append({
                "tenant_id": _serialize(obj.tenant_id),
                "channel_id": obj.channel_id,
                "channel_name": obj.channel_name,
                "channel_url": obj.channel_url,
                "owned_by_tenant": obj.owned_by_tenant,
                "primary_channel": obj.primary_channel,
                "daily_quota_limit": obj.daily_quota_limit,
                "quota_used_today": obj.quota_used_today,
                "status": obj.status,
                "verification_status": obj.verification_status,
                "assigned_teacher_id": _serialize(obj.assigned_teacher_id),
                "scopes": obj.scopes,
            })

        class_link_configs = []
        for obj in ClassLinkConfig.objects.all():
            class_link_configs.append({
                "tenant_id": _serialize(obj.tenant_id),
                "platform": obj.platform,
                "is_active": obj.is_active,
                "is_default": obj.is_default,
                "api_endpoint": obj.api_endpoint,
                "api_key_reference": obj.api_key_reference,
                "client_id": obj.client_id,
                "client_secret_reference": obj.client_secret_reference,
                "oauth_token_reference": obj.oauth_token_reference,
                "webhook_url": obj.webhook_url,
                "auto_generate_link": obj.auto_generate_link,
                "generate_minutes_before": obj.generate_minutes_before,
                "default_duration_minutes": obj.default_duration_minutes,
                "auto_record": obj.auto_record,
                "auto_admit_participants": obj.auto_admit_participants,
                "config_json": obj.config_json,
            })

        yt_integrations = []
        for obj in IntegrationConfig.objects.filter(integration_type="YOUTUBE"):
            yt_integrations.append({
                "tenant_id": _serialize(obj.tenant_id),
                "name": obj.name,
                "description": obj.description,
                "provider": obj.provider,
                "api_endpoint": obj.api_endpoint,
                "api_key": obj.api_key,
                "api_secret": obj.api_secret,
                "oauth_client_id": obj.oauth_client_id,
                "oauth_client_secret": obj.oauth_client_secret,
                "channel_id": obj.channel_id,
                "channel_name": obj.channel_name,
                "playlist_ids": obj.playlist_ids,
                "auto_sync_videos": obj.auto_sync_videos,
                "max_requests_per_hour": obj.max_requests_per_hour,
                "max_requests_per_user": obj.max_requests_per_user,
                "is_active": obj.is_active,
                "is_verified": obj.is_verified,
                "health_status": obj.health_status,
                "config_json": obj.config_json,
                "usage_stats": obj.usage_stats,
            })

        payload = {
            "exported_at": timezone.now().isoformat(),
            "youtube_channels": yt_channels,
            "class_link_configs": class_link_configs,
            "youtube_integrations": yt_integrations,
        }

        with output_path.open("w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, sort_keys=True)

        self.stdout.write(self.style.SUCCESS(f"Exported Live Classes & YouTube configuration to {output_path}"))
