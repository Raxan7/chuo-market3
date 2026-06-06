import logging
import time

from django.core.management.base import BaseCommand
from django.db import transaction, close_old_connections
from django.db.models import Count
from django.utils import timezone

from lms.models import QuizGenerationJob, Quiz
from lms.ai_assessments import ensure_module_assessment

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Processes queued AI quiz generation jobs with visible progress output."

    def add_arguments(self, parser):
        parser.add_argument(
            "--limit",
            type=int,
            default=3,
            help="Maximum number of pending jobs to process in this run.",
        )
        parser.add_argument(
            "--retry-stuck-after-minutes",
            type=int,
            default=30,
            help="Reset processing jobs that have been stuck longer than this.",
        )
        parser.add_argument(
            "--show-summary-only",
            action="store_true",
            help="Only show queue summary without processing jobs.",
        )

    def handle(self, *args, **options):
        started_at = time.time()
        limit = options["limit"]
        retry_stuck_after_minutes = options["retry_stuck_after_minutes"]

        self.stdout.write("")
        self.stdout.write(self.style.MIGRATE_HEADING("AI Quiz Generation Queue"))
        self.stdout.write("=" * 60)

        self._reset_stuck_jobs(retry_stuck_after_minutes)
        self._print_queue_summary()

        if options["show_summary_only"]:
            self.stdout.write("")
            self.stdout.write(self.style.SUCCESS("Summary displayed. No jobs processed."))
            return

        jobs = self._lock_pending_jobs(limit)

        if not jobs:
            self.stdout.write("")
            self.stdout.write(self.style.WARNING("No pending jobs found."))
            self.stdout.write("Nothing to process right now.")
            return

        total_selected = len(jobs)

        self.stdout.write("")
        self.stdout.write(self.style.NOTICE(f"Selected {total_selected} job(s) for this run."))
        self.stdout.write("-" * 60)

        completed_count = 0
        failed_count = 0
        retried_count = 0

        for index, job in enumerate(jobs, start=1):
            close_old_connections()

            progress_percent = round((index / total_selected) * 100, 1)
            module = job.module
            course_title = getattr(module.course, "title", "Unknown course")

            self.stdout.write("")
            self.stdout.write(
                self.style.MIGRATE_LABEL(
                    f"[{index}/{total_selected}] {progress_percent}% - Processing job #{job.id}"
                )
            )
            self.stdout.write(f"Course: {course_title}")
            self.stdout.write(f"Module: {module.title}")
            self.stdout.write(f"Module ID: {module.id}")
            self.stdout.write(f"Question count: {job.question_count}")
            self.stdout.write(f"Force regenerate: {job.force}")
            self.stdout.write(f"Attempt: {job.attempts + 1}/{job.max_attempts}")

            job_start = time.time()

            try:
                quiz = ensure_module_assessment(
                    module,
                    question_count=job.question_count,
                    force=job.force,
                )

                question_total = quiz.questions.count() if quiz else 0

                job.status = "completed"
                job.completed_at = timezone.now()
                job.error = ""
                job.save(update_fields=["status", "completed_at", "error", "updated_at"])

                completed_count += 1
                elapsed = round(time.time() - job_start, 2)

                self.stdout.write(
                    self.style.SUCCESS(
                        f"SUCCESS: Generated quiz for module '{module.title}' "
                        f"with {question_total} question(s) in {elapsed}s."
                    )
                )

            except Exception as exc:
                job.attempts += 1
                job.error = str(exc)

                if job.attempts >= job.max_attempts:
                    job.status = "failed"
                    job.completed_at = timezone.now()

                    Quiz.objects.filter(
                        module=module,
                        generated_for__isnull=True,
                        draft=False,
                    ).update(
                        generation_status="failed",
                        generation_message=(
                            f"AI generation failed after {job.attempts} attempt(s): {str(exc)[:300]}"
                        ),
                        generation_completed_at=timezone.now(),
                    )

                    failed_count += 1

                    self.stdout.write(
                        self.style.ERROR(
                            f"FAILED: Job #{job.id} failed permanently after "
                            f"{job.attempts}/{job.max_attempts} attempts."
                        )
                    )
                else:
                    job.status = "pending"
                    job.locked_at = None

                    retried_count += 1

                    self.stdout.write(
                        self.style.WARNING(
                            f"RETRY: Job #{job.id} failed, but will be retried. "
                            f"Attempts: {job.attempts}/{job.max_attempts}"
                        )
                    )

                job.save(
                    update_fields=[
                        "status",
                        "attempts",
                        "error",
                        "locked_at",
                        "completed_at",
                        "updated_at",
                    ]
                )

                logger.exception("Error processing quiz generation job %s", job.id)

            finally:
                close_old_connections()

        total_elapsed = round(time.time() - started_at, 2)

        self.stdout.write("")
        self.stdout.write("=" * 60)
        self.stdout.write(self.style.MIGRATE_HEADING("Run finished"))
        self.stdout.write(f"Processed this run: {total_selected}")
        self.stdout.write(self.style.SUCCESS(f"Completed: {completed_count}"))
        self.stdout.write(self.style.WARNING(f"Returned to pending for retry: {retried_count}"))
        self.stdout.write(self.style.ERROR(f"Failed permanently: {failed_count}"))
        self.stdout.write(f"Elapsed time: {total_elapsed}s")

        self.stdout.write("")
        self._print_queue_summary()

    def _lock_pending_jobs(self, limit):
        """
        Select pending jobs and mark them processing in one short transaction.
        The heavy AI generation happens outside this transaction.
        """
        with transaction.atomic():
            jobs = list(
                QuizGenerationJob.objects.select_for_update(skip_locked=True)
                .select_related("module", "module__course")
                .filter(
                    status="pending",
                    attempts__lt=models_f_max_attempts_safe(),
                )
                .order_by("-force", "created_at")[:limit]
            )

            now = timezone.now()

            for job in jobs:
                job.status = "processing"
                job.started_at = now
                job.locked_at = now
                job.save(
                    update_fields=[
                        "status",
                        "started_at",
                        "locked_at",
                        "updated_at",
                    ]
                )

        return jobs

    def _reset_stuck_jobs(self, minutes):
        """
        If a cron run dies halfway, some jobs may remain stuck as processing.
        This safely returns old processing jobs back to pending.
        """
        cutoff = timezone.now() - timezone.timedelta(minutes=minutes)

        stuck_jobs = QuizGenerationJob.objects.filter(
            status="processing",
            locked_at__lt=cutoff,
            attempts__lt=models_f_max_attempts_safe(),
        )

        count = stuck_jobs.update(
            status="pending",
            locked_at=None,
            error="Reset because job was stuck in processing.",
            updated_at=timezone.now(),
        )

        if count:
            self.stdout.write(
                self.style.WARNING(
                    f"Reset {count} stuck processing job(s) back to pending."
                )
            )

    def _print_queue_summary(self):
        summary = {
            item["status"]: item["total"]
            for item in QuizGenerationJob.objects.values("status").annotate(total=Count("id"))
        }

        pending = summary.get("pending", 0)
        processing = summary.get("processing", 0)
        completed = summary.get("completed", 0)
        failed = summary.get("failed", 0)
        total = pending + processing + completed + failed

        if total:
            done_percent = round(((completed + failed) / total) * 100, 1)
        else:
            done_percent = 100

        self.stdout.write("")
        self.stdout.write("Queue summary:")
        self.stdout.write(f"Pending: {pending}")
        self.stdout.write(f"Processing: {processing}")
        self.stdout.write(f"Completed: {completed}")
        self.stdout.write(f"Failed: {failed}")
        self.stdout.write(f"Total jobs: {total}")
        self.stdout.write(f"Overall progress: {done_percent}%")


def models_f_max_attempts_safe():
    """
    Import F lazily so this command stays simple and avoids top-level confusion.
    """
    from django.db.models import F

    return F("max_attempts")
