"""Move legacy payment-proof files from public MEDIA_ROOT to PRIVATE_MEDIA_ROOT."""
from pathlib import Path
import shutil

from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Move payment proof files from MEDIA_ROOT into private storage.'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true')

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        public_root = Path(settings.MEDIA_ROOT)
        private_root = Path(settings.PRIVATE_MEDIA_ROOT)
        prefixes = ('payment_proofs', 'lms/payment_proofs')
        moved = 0

        for prefix in prefixes:
            source_dir = public_root / prefix
            if not source_dir.exists():
                continue
            for source in source_dir.rglob('*'):
                if not source.is_file():
                    continue
                relative = source.relative_to(public_root)
                destination = private_root / relative
                self.stdout.write(f'{source} -> {destination}')
                if not dry_run:
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    if destination.exists():
                        self.stderr.write(self.style.WARNING(f'Skipping existing file: {destination}'))
                        continue
                    shutil.move(str(source), str(destination))
                moved += 1

        suffix = 'would be moved' if dry_run else 'moved'
        self.stdout.write(self.style.SUCCESS(f'{moved} payment proof file(s) {suffix}.'))
