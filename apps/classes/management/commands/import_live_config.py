import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from classes.models import YouTubeChannel
from system_config.models import ClassLinkConfig, IntegrationConfig


class Command(BaseCommand):
    """Import Live Classes & YouTube configuration from a JSON file.

    This is intended for migrating or restoring configuration between environments.
    It is **idempotent**: it uses update_or_create keyed by (tenant_id, unique fields).

    WARNING: Does not delete existing records; it only creates/updates.
    """

    help = "Import Live Classes & YouTube configuration from JSON"

    def add_arguments(self, parser):
        parser.add_argument(
            "input",
            help="Input JSON file path (e.g. export/live_config.json)",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        input_path = Path(options["input"]).resolve()
        if not input_path.exists():
            raise CommandError(f"Input file not found: {input_path}")

        self.stdout.write(self.style.MIGRATE_HEADING(f"Importing Live Classes & YouTube configuration from {input_path}..."))

        with input_path.open("r", encoding="utf-8") as f:
            data = json.load(f)

        yt_channels = data.get("youtube_channels", [])
        cl_configs = data.get("class_link_configs", [])
        yt_integrations = data.get("youtube_integrations", [])

        # YouTube Channels
        self.stdout.write(self.style.HTTP_INFO(f"YouTubeChannel: {len(yt_channels)} record(s)"))
        for row in yt_channels:
            tenant_id = row.pop("tenant_id")
            channel_id = row.pop("channel_id")
            obj, created = YouTubeChannel.objects.update_or_create(
                tenant_id=tenant_id,
                channel_id=channel_id,
                defaults=row,
            )
            self.stdout.write(f"  - {'CREATED' if created else 'UPDATED'} YouTubeChannel {obj.channel_name} ({obj.channel_id})")

        # Class Link Configs
        self.stdout.write(self.style.HTTP_INFO(f"ClassLinkConfig: {len(cl_configs)} record(s)"))
        for row in cl_configs:
            tenant_id = row.pop("tenant_id")
            platform = row.pop("platform")
            obj, created = ClassLinkConfig.objects.update_or_create(
                tenant_id=tenant_id,
                platform=platform,
                defaults=row,
            )
            self.stdout.write(f"  - {'CREATED' if created else 'UPDATED'} ClassLinkConfig {obj.platform} for tenant {obj.tenant_id}")

        # YouTube IntegrationConfig
        self.stdout.write(self.style.HTTP_INFO(f"IntegrationConfig[YOUTUBE]: {len(yt_integrations)} record(s)"))
        for row in yt_integrations:
            tenant_id = row.pop("tenant_id")
            # Use (tenant, provider, name) as a natural key
            name = row.pop("name")
            provider = row.get("provider")
            obj, created = IntegrationConfig.objects.update_or_create(
                tenant_id=tenant_id,
                integration_type="YOUTUBE",
                provider=provider,
                name=name,
                defaults=row,
            )
            self.stdout.write(f"  - {'CREATED' if created else 'UPDATED'} YouTube IntegrationConfig {obj.name} ({obj.provider})")

        self.stdout.write(self.style.SUCCESS("Import completed successfully."))
