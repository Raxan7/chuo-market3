import logging
import time

from django.core.management.base import BaseCommand
from django.db import transaction, close_old_connections
from django.db.models import Count, F
from django.utils import timezone

from lms.models import QuizGenerationJob, Quiz
from lms.ai_assessments import ensure_module_assessment

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Processes queued AI quiz generation jobs with detailed progress logs."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=3)
        parser.add_argument("--sleep", type=float, default=3.0)
        parser.add_argument("--retry-stuck-after-minutes", type=int, default=10)
        parser.add_argument("--show-summary-only", action="store_true")
        parser.add_argument("--reset-all-processing", action="store_true")

    def handle(self, *args, **options):
        run_started = time.time()

        limit = options["limit"]
        sleep_seconds = options["sleep"]
        retry_stuck_after_minutes = options["retry_stuck_after_minutes"]

        self.stdout.write("")
        self.stdout.write(self.style.MIGRATE_HEADING("AI Quiz Generation Queue"))
        self.stdout.write("=" * 70)

        if options["reset_all_processing"]:
            self._reset_all_processing_jobs()

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
        self.stdout.write(f"Sleep between jobs: {sleep_seconds}s")
        self.stdout.write("-" * 70)

        completed_count = 0
        failed_count = 0
        retried_count = 0

        for index, job in enumerate(jobs, start=1):
            close_old_connections()

            job_started = time.time()
            module = job.module
            course = module.course

            progress = round((index / total_selected) * 100, 1)

            self.stdout.write("")
            self.stdout.write(self.style.MIGRATE_LABEL(
                f"[{index}/{total_selected}] {progress}% | Job #{job.id}"
            ))
            self.stdout.write(f"Course ID: {course.id}")
            self.stdout.write(f"Course: {course.title}")
            self.stdout.write(f"Module ID: {module.id}")
            self.stdout.write(f"Module: {module.title}")
            self.stdout.write(f"Question count: {job.question_count}")
            self.stdout.write(f"Force regenerate: {job.force}")
            self.stdout.write(f"Attempt: {job.attempts + 1}/{job.max_attempts}")
            self.stdout.write(f"Job created: {job.created_at}")
            self.stdout.write(f"Job locked at: {job.locked_at}")
            self.stdout.write("Status: calling AI generation...")

            logger.info(
                "Starting quiz job id=%s module_id=%s course_id=%s attempt=%s/%s force=%s",
                job.id,
                module.id,
                course.id,
                job.attempts + 1,
                job.max_attempts,
                job.force,
            )

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

                elapsed = round(time.time() - job_started, 2)
                completed_count += 1

                self.stdout.write(self.style.SUCCESS(
                    f"SUCCESS: Job #{job.id} completed in {elapsed}s. "
                    f"Quiz #{quiz.id if quiz else 'N/A'} has {question_total} question(s)."
                ))

                logger.info(
                    "Completed quiz job id=%s module_id=%s quiz_id=%s questions=%s elapsed=%ss",
                    job.id,
                    module.id,
                    quiz.id if quiz else None,
                    question_total,
                    elapsed,
                )

            except KeyboardInterrupt:
                self.stdout.write("")
                self.stdout.write(self.style.WARNING(
                    "KeyboardInterrupt detected. Returning current job to pending before exit..."
                ))

                job.status = "pending"
                job.locked_at = None
                job.started_at = None
                job.error = "Interrupted by user; returned to pending."
                job.save(update_fields=["status", "locked_at", "started_at", "error", "updated_at"])

                raise

            except Exception as exc:
                elapsed = round(time.time() - job_started, 2)

                job.attempts += 1
                job.error = str(exc)

                self.stdout.write(self.style.ERROR(
                    f"ERROR: Job #{job.id} failed after {elapsed}s."
                ))
                self.stdout.write(f"Reason: {str(exc)[:1000]}")

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

                    self.stdout.write(self.style.ERROR(
                        f"FAILED PERMANENTLY: Job #{job.id} reached "
                        f"{job.attempts}/{job.max_attempts} attempts."
                    ))

                    logger.exception(
                        "Quiz job permanently failed id=%s module_id=%s attempts=%s error=%s",
                        job.id,
                        module.id,
                        job.attempts,
                        exc,
                    )

                else:
                    job.status = "pending"
                    job.locked_at = None
                    job.started_at = None

                    retried_count += 1

                    self.stdout.write(self.style.WARNING(
                        f"RETRY: Job #{job.id} returned to pending. "
                        f"Attempts: {job.attempts}/{job.max_attempts}"
                    ))

                    logger.exception(
                        "Quiz job will retry id=%s module_id=%s attempts=%s/%s error=%s",
                        job.id,
                        module.id,
                        job.attempts,
                        job.max_attempts,
                        exc,
                    )

                job.save(update_fields=[
                    "status",
                    "attempts",
                    "error",
                    "locked_at",
                    "started_at",
                    "completed_at",
                    "updated_at",
                ])

            finally:
                close_old_connections()

            if index < total_selected and sleep_seconds > 0:
                self.stdout.write(f"Waiting {sleep_seconds}s before next job...")
                time.sleep(sleep_seconds)

        total_elapsed = round(time.time() - run_started, 2)

        self.stdout.write("")
        self.stdout.write("=" * 70)
        self.stdout.write(self.style.MIGRATE_HEADING("Run finished"))
        self.stdout.write(f"Processed this run: {total_selected}")
        self.stdout.write(self.style.SUCCESS(f"Completed: {completed_count}"))
        self.stdout.write(self.style.WARNING(f"Returned to pending for retry: {retried_count}"))
        self.stdout.write(self.style.ERROR(f"Failed permanently: {failed_count}"))
        self.stdout.write(f"Elapsed time: {total_elapsed}s")

        self._print_queue_summary()

    def _lock_pending_jobs(self, limit):
        with transaction.atomic():
            jobs = list(
                QuizGenerationJob.objects.select_for_update(skip_locked=True)
                .select_related("module", "module__course")
                .filter(status="pending", attempts__lt=F("max_attempts"))
                .order_by("-force", "attempts", "created_at")[:limit]
            )

            now = timezone.now()

            for job in jobs:
                job.status = "processing"
                job.started_at = now
                job.locked_at = now
                job.save(update_fields=[
                    "status",
                    "started_at",
                    "locked_at",
                    "updated_at",
                ])

        return jobs

    def _reset_stuck_jobs(self, minutes):
        cutoff = timezone.now() - timezone.timedelta(minutes=minutes)

        stuck_jobs = QuizGenerationJob.objects.filter(
            status="processing",
            locked_at__lt=cutoff,
            attempts__lt=F("max_attempts"),
        )

        count = stuck_jobs.update(
            status="pending",
            locked_at=None,
            started_at=None,
            error=f"Reset because job was stuck in processing for more than {minutes} minute(s).",
            updated_at=timezone.now(),
        )

        if count:
            self.stdout.write(self.style.WARNING(
                f"Reset {count} stuck processing job(s) back to pending."
            ))

    def _reset_all_processing_jobs(self):
        count = QuizGenerationJob.objects.filter(status="processing").update(
            status="pending",
            locked_at=None,
            started_at=None,
            error="Manually reset from processing to pending.",
            updated_at=timezone.now(),
        )

        self.stdout.write(self.style.WARNING(
            f"Manually reset {count} processing job(s) back to pending."
        ))

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

        done_percent = round(((completed + failed) / total) * 100, 1) if total else 100

        self.stdout.write("")
        self.stdout.write("Queue summary:")
        self.stdout.write(f"Pending: {pending}")
        self.stdout.write(f"Processing: {processing}")
        self.stdout.write(f"Completed: {completed}")
        self.stdout.write(f"Failed: {failed}")
        self.stdout.write(f"Total jobs: {total}")
        self.stdout.write(f"Overall progress: {done_percent}%")