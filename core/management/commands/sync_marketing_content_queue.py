from django.core.management.base import BaseCommand

from core.content_marketing import (
    _pending_content_jobs_newest_first,
    rebalance_content_schedule,
    sync_content_jobs,
)


class Command(BaseCommand):
    help = 'Backfill/synchronize all eligible ChuoSmart content into the newest-first marketing content queue.'

    def add_arguments(self, parser):
        parser.add_argument('--limit', type=int, default=0, help='0 means all eligible content.')
        parser.add_argument('--preview', type=int, default=20, help='Number of planned queue rows to print.')

    def handle(self, *args, **options):
        limit = int(options['limit']) or None
        result = sync_content_jobs(limit=limit)
        schedule = rebalance_content_schedule()
        self.stdout.write(self.style.SUCCESS(
            f"Content queue synchronized: created={result['created']}, existing={result['existing']}, "
            f"pending/scheduled={schedule['scheduled']}."
        ))
        rows = _pending_content_jobs_newest_first()[:max(0, int(options['preview']))]
        for published_at, job, instance in rows:
            self.stdout.write(
                f'{job.run_after.isoformat()} | {published_at.isoformat()} | '
                f'{job.job_type}:{job.object_id} | {getattr(instance, "title", instance)}'
            )
