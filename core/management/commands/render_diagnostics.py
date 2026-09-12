import os
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Validate ChuoSmart's optional Render/Docker deployment configuration."

    def handle(self, *args, **options):
        errors = []
        base_dir = Path(settings.BASE_DIR)

        expected_files = (
            "Dockerfile",
            ".dockerignore",
            "render.yaml",
            "deploy/render/start.sh",
            "Commerce/settings/render.py",
        )

        self.stdout.write("=== ChuoSmart Render diagnostics ===")
        self.stdout.write(f"DJANGO_ENV={os.getenv('DJANGO_ENV', '')}")
        self.stdout.write(
            f"SETTINGS_MODULE={os.getenv('DJANGO_SETTINGS_MODULE', 'Commerce.settings')}"
        )
        self.stdout.write(f"DATABASE_ENGINE={settings.DATABASES['default']['ENGINE']}")
        self.stdout.write(f"DEBUG={settings.DEBUG}")
        self.stdout.write(
            f"CANONICAL_REDIRECT_ENABLED={getattr(settings, 'CANONICAL_REDIRECT_ENABLED', None)}"
        )
        self.stdout.write(f"EMAIL_BACKEND={settings.EMAIL_BACKEND}")

        if os.getenv("DJANGO_ENV", "").strip().lower() != "render":
            errors.append("DJANGO_ENV must be 'render' for this diagnostic.")
        if settings.DEBUG:
            errors.append("Render settings must not run with DEBUG=True.")
        if getattr(settings, "CANONICAL_REDIRECT_ENABLED", True):
            errors.append("Render prototype must not redirect to chuosmart.com.")

        for relative in expected_files:
            path = base_dir / relative
            if path.exists():
                self.stdout.write(self.style.SUCCESS(f"FILE_OK={relative}"))
            else:
                errors.append(f"Missing deployment file: {relative}")

        hostname = os.getenv("RENDER_EXTERNAL_HOSTNAME", "").strip()
        if hostname and hostname not in settings.ALLOWED_HOSTS:
            errors.append(
                "RENDER_EXTERNAL_HOSTNAME is not present in Django ALLOWED_HOSTS."
            )

        if errors:
            for error in errors:
                self.stderr.write(self.style.ERROR(f"ERROR={error}"))
            raise CommandError("Render diagnostics failed.")

        self.stdout.write(
            self.style.SUCCESS(
                "Render diagnostics passed: container files and isolated settings are healthy."
            )
        )
