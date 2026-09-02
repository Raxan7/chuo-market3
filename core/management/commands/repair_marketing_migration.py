from django.core.management.base import BaseCommand, CommandError
from django.db import connection
from django.db.migrations.recorder import MigrationRecorder

from core.models import MarketingCampaign, MarketingDelivery, MarketingSuppression


class Command(BaseCommand):
    help = (
        'Safely remove tables left by a failed, unrecorded core.0034_marketing_engine migration. '
        'Use this after MariaDB error 1071 before rerunning migrate.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--force', action='store_true',
            help='Allow reset even if partial marketing tables contain rows. Normally the command refuses.',
        )

    def handle(self, *args, **options):
        applied = MigrationRecorder(connection).migration_qs.filter(
            app='core', name='0034_marketing_engine'
        ).exists()
        if applied:
            self.stdout.write(self.style.SUCCESS(
                'core.0034_marketing_engine is already recorded as applied; no partial-migration reset is needed.'
            ))
            return

        existing = set(connection.introspection.table_names())
        models = [MarketingDelivery, MarketingCampaign, MarketingSuppression]
        present_models = [model for model in models if model._meta.db_table in existing]
        present_tables = {model._meta.db_table for model in present_models}
        if not present_models:
            self.stdout.write('No partial marketing tables were found. You can run python manage.py migrate.')
            return

        counts = {}
        with connection.cursor() as cursor:
            for model in present_models:
                table = connection.ops.quote_name(model._meta.db_table)
                cursor.execute(f'SELECT COUNT(*) FROM {table}')
                counts[model._meta.db_table] = int(cursor.fetchone()[0])

        total_rows = sum(counts.values())
        self.stdout.write(f'Unrecorded partial marketing tables found: {counts}')
        if total_rows and not options['force']:
            raise CommandError(
                'Partial marketing tables contain data. Refusing to drop them automatically. '
                'Inspect the data first or rerun with --force only if it is safe to discard.'
            )

        # Reverse dependency order. These tables belong exclusively to the failed
        # marketing migration and cannot contain valid production campaign data if
        # the migration was never recorded as applied.
        with connection.schema_editor() as schema_editor:
            for model in models:
                if model._meta.db_table in present_tables:
                    self.stdout.write(f'Dropping partial table {model._meta.db_table} ...')
                    schema_editor.delete_model(model)

        remaining = present_tables.intersection(connection.introspection.table_names())
        if remaining:
            raise CommandError(
                'Marketing migration repair did not fully remove the partial schema. '
                f'Remaining table(s): {sorted(remaining)}. Do not run migrate until these are resolved.'
            )

        self.stdout.write(self.style.SUCCESS(
            'Partial marketing schema removed and verified. Rerun python manage.py migrate; '
            'the corrected 0034 migration can now apply cleanly.'
        ))
