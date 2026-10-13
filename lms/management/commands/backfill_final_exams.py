from django.core.management.base import BaseCommand
from django.utils import timezone

from lms.ai_assessments import (
    _archive_attempted_quiz_for_regeneration,
    _quiz_has_valid_question_set,
    queue_module_assessment_generation,
)
from lms.assessment_policy import (
    FINAL_EXAM_QUESTION_COUNT,
    final_assessed_module,
)
from lms.models import (
    Course,
    Quiz,
    QuizGenerationJob,
    QuizTaker,
)


class Command(BaseCommand):
    help = (
        "Safely backfill 20-question Final Exams. "
        "Dry-run unless --apply is supplied."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--apply",
            action="store_true",
        )

    def handle(self, *args, **options):
        apply_changes = options["apply"]

        stats = {
            "courses": 0,
            "ready": 0,
            "repaired": 0,
            "queued": 0,
            "versioned": 0,
            "active_skipped": 0,
        }

        print()
        print("=" * 100)
        print(
            "FINAL EXAM BACKFILL",
            "APPLY" if apply_changes else "DRY RUN",
        )
        print("=" * 100)

        for course in Course.objects.all().order_by(
            "id"
        ):
            module = final_assessed_module(
                course
            )

            if not module:
                continue

            stats["courses"] += 1

            quiz = (
                Quiz.objects.filter(
                    module=module,
                    generated_for__isnull=True,
                    draft=False,
                )
                .order_by("id")
                .first()
            )

            if (
                quiz
                and _quiz_has_valid_question_set(
                    quiz,
                    FINAL_EXAM_QUESTION_COUNT,
                )
            ):
                stats["ready"] += 1

                if quiz.generation_status != "ready":
                    print(
                        "REPAIR",
                        course.id,
                        module.id,
                        quiz.id,
                    )

                    if apply_changes:
                        quiz.generation_status = "ready"
                        quiz.generation_message = (
                            "Quiz is ready."
                        )
                        quiz.generation_completed_at = (
                            timezone.now()
                        )

                        quiz.save(
                            update_fields=[
                                "generation_status",
                                "generation_message",
                                "generation_completed_at",
                            ]
                        )

                        stats["repaired"] += 1
                else:
                    print(
                        "READY ",
                        course.id,
                        module.id,
                        quiz.id,
                    )

                # Cancel stale regeneration jobs that could later
                # downgrade the status of a valid 20Q exam.
                if apply_changes:
                    (
                        QuizGenerationJob.objects
                        .filter(
                            module=module,
                            status__in=[
                                "pending",
                                "processing",
                            ],
                        )
                        .update(
                            status="completed",
                            error="",
                            completed_at=timezone.now(),
                            locked_at=None,
                        )
                    )

                continue

            attempts = (
                QuizTaker.objects.filter(
                    quiz=quiz
                )
                if quiz
                else QuizTaker.objects.none()
            )

            active = attempts.filter(
                completed=False,
            ).count()

            completed = attempts.filter(
                completed=True,
            ).count()

            if active:
                stats["active_skipped"] += 1

                print(
                    "SKIP ACTIVE",
                    course.id,
                    module.id,
                    "active_attempts=",
                    active,
                )

                continue

            if completed:
                print(
                    "VERSION",
                    course.id,
                    module.id,
                    "historical_attempts=",
                    completed,
                )

                if apply_changes:
                    _archive_attempted_quiz_for_regeneration(
                        quiz
                    )

                    stats["versioned"] += 1

                    queue_module_assessment_generation(
                        module,
                        question_count=(
                            FINAL_EXAM_QUESTION_COUNT
                        ),
                        force=True,
                    )

                    stats["queued"] += 1

                continue

            count = (
                quiz.questions.count()
                if quiz
                else 0
            )

            print(
                "QUEUE",
                course.id,
                module.id,
                "current_questions=",
                count,
            )

            if apply_changes:
                queue_module_assessment_generation(
                    module,
                    question_count=(
                        FINAL_EXAM_QUESTION_COUNT
                    ),
                    force=True,
                )

                stats["queued"] += 1

        print()
        print("=" * 100)

        for key, value in stats.items():
            print(
                f"{key.upper()}={value}"
            )

        if not apply_changes:
            print(
                "DRY RUN ONLY. "
                "Use --apply after reviewing."
            )
        else:
            print(
                "Backfill queued safely."
            )
