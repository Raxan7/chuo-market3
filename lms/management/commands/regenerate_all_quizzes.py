import logging
import sys
import time

from django.core.management.base import BaseCommand
from django.db import close_old_connections

from lms.models import CourseModule, Quiz
from lms.ai_assessments import ensure_module_assessment

logger = logging.getLogger(__name__)


def safe_text(text):
    if isinstance(text, str):
        return text.encode('utf-8', errors='replace').decode('utf-8', errors='replace')
    return text


class Command(BaseCommand):
    help = "Regenerates non-AI module quizzes via Cerebras. Skips ai_generated=True. Terminates on error."

    def add_arguments(self, parser):
        parser.add_argument("--course-id", type=int, help="Only regenerate for a specific course ID")
        parser.add_argument("--question-count", type=int, default=5)
        parser.add_argument("--sleep", type=float, default=30.0, help="Seconds between modules (rate limiting)")
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument("--start-at", type=int, default=0, help="Skip first N modules (for resuming)")
        parser.add_argument("--max-modules", type=int, default=0, help="Max modules to process (0 = all)")
        parser.add_argument("--force", action="store_true", help="Regenerate even ai_generated=True quizzes")

    def write(self, msg, style=None):
        msg = safe_text(msg)
        if style:
            self.stdout.write(style(msg))
        else:
            self.stdout.write(msg)

    def error(self, msg):
        self.stderr.write(self.style.ERROR(safe_text(msg)))

    def handle(self, *args, **options):
        question_count = options["question_count"]
        sleep_seconds = options["sleep"]
        dry_run = options["dry_run"]
        start_at = options["start_at"]
        max_modules = options["max_modules"]
        force = options["force"]

        modules_qs = CourseModule.objects.filter(skip_assessment=False).order_by("course__title", "order", "id")
        if options["course_id"]:
            modules_qs = modules_qs.filter(course_id=options["course_id"])

        modules = list(modules_qs)
        total_all = len(modules)

        # Separate already-AI-generated from needing-generation
        already_done = []
        needs_gen = []
        for m in modules:
            q = Quiz.objects.filter(module=m, generated_for__isnull=True, draft=False).first()
            if q and q.ai_generated and not force:
                already_done.append(m)
            else:
                needs_gen.append(m)

        if start_at > 0:
            if start_at > len(needs_gen):
                self.error(f"--start-at={start_at} exceeds modules needing gen ({len(needs_gen)})")
                sys.exit(1)
            needs_gen = needs_gen[start_at:]

        if max_modules > 0:
            needs_gen = needs_gen[:max_modules]

        total = len(needs_gen)

        self.write("")
        self.write("Cerebras AI Quiz Regeneration", self.style.MIGRATE_HEADING)
        self.write("=" * 70)
        self.write(f"Total modules (no skip): {total_all}")
        self.write(f"Already AI-generated (skipped): {len(already_done)}")
        self.write(f"Need generation: {total}")
        self.write(f"Skipped via --start-at: {start_at}")
        self.write(f"Questions per quiz: {question_count}")
        self.write(f"Sleep between modules: {sleep_seconds}s")
        self.write(f"Force regenerate: {force}")
        self.write(f"Dry run: {dry_run}")
        self.write("-" * 70)

        if dry_run:
            for i, m in enumerate(needs_gen):
                self.write(f"  [{i+1}/{total}] M#{m.id} [{m.course.title}] {m.title}")
            self.write(f"Dry run complete. {total} module(s) would be processed.", self.style.SUCCESS)
            return

        completed = 0

        for index, module in enumerate(needs_gen):
            close_old_connections()

            idx = start_at + index + 1
            self.write("")
            self.write(f"[{idx}/{total}] Module #{module.id}", self.style.NOTICE)
            self.write(f"  Course: {safe_text(module.course.title)}")
            self.write(f"  Module: {safe_text(module.title)}")

            try:
                quiz = ensure_module_assessment(
                    module,
                    question_count=question_count,
                    force=True,
                )

                question_total = quiz.questions.count() if quiz else 0
                self.write(f"  OK: Quiz #{quiz.id} ready - {question_total} question(s)", self.style.SUCCESS)
                completed += 1

            except Exception as exc:
                self.write(f"  FAILED: {exc}", self.style.ERROR)
                self.error(
                    f"\nFATAL: Quiz generation failed for Module #{module.id} \"{safe_text(module.title)}\""
                    f"\n  Course: {safe_text(module.course.title)}"
                    f"\n  Error: {exc}"
                    f"\n\nTERMINATING. Fix the issue, then re-run with --start-at {idx} to continue."
                )
                logger.exception(
                    "Quiz generation failed for module_id=%s course_id=%s",
                    module.id, module.course.id,
                )
                sys.exit(1)

            if index < total - 1 and sleep_seconds > 0:
                self.write(f"  Waiting {sleep_seconds}s...")
                time.sleep(sleep_seconds)

        self.write("")
        self.write("=" * 70)
        self.write(f"Done. {completed}/{total} module(s) completed successfully.", self.style.SUCCESS)
