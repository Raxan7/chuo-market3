import re

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from django.utils.html import strip_tags
from django.utils.text import Truncator

from lms.models import QuizGenerationJob, Quiz, MCQuestion, Choice


class Command(BaseCommand):
    help = "Creates emergency fallback quizzes for pending/failed quiz generation jobs."

    def add_arguments(self, parser):
        parser.add_argument(
            "--limit",
            type=int,
            default=50,
            help="Maximum number of jobs to fallback-generate in this run.",
        )
        parser.add_argument(
            "--include-failed",
            action="store_true",
            help="Also process failed jobs.",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Replace existing non-ready or failed quizzes.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Preview what would happen without writing changes.",
        )

    def handle(self, *args, **options):
        limit = options["limit"]
        include_failed = options["include_failed"]
        force = options["force"]
        dry_run = options["dry_run"]

        statuses = ["pending", "processing"]
        if include_failed:
            statuses.append("failed")

        jobs = (
            QuizGenerationJob.objects
            .select_related("module", "module__course")
            .filter(status__in=statuses)
            .order_by("created_at")[:limit]
        )

        total = jobs.count()

        self.stdout.write("")
        self.stdout.write(self.style.MIGRATE_HEADING("Emergency Fallback Quiz Generator"))
        self.stdout.write("=" * 70)
        self.stdout.write(f"Selected jobs: {total}")
        self.stdout.write(f"Include failed: {include_failed}")
        self.stdout.write(f"Force replace: {force}")
        self.stdout.write(f"Dry run: {dry_run}")
        self.stdout.write("-" * 70)

        if total == 0:
            self.stdout.write(self.style.SUCCESS("No matching jobs found."))
            return

        completed = 0
        skipped = 0

        for index, job in enumerate(jobs, start=1):
            module = job.module
            course = module.course

            self.stdout.write("")
            self.stdout.write(f"[{index}/{total}] Job #{job.id}")
            self.stdout.write(f"Course: {course.title}")
            self.stdout.write(f"Module #{module.id}: {module.title}")

            quiz = Quiz.objects.filter(
                module=module,
                generated_for__isnull=True,
                draft=False,
            ).order_by("id").first()

            if quiz and quiz.generation_status == "ready" and quiz.questions.exists() and not force:
                skipped += 1
                self.stdout.write(self.style.WARNING(
                    f"SKIPPED: Quiz #{quiz.id} is already ready with {quiz.questions.count()} question(s)."
                ))
                continue

            if dry_run:
                self.stdout.write(self.style.WARNING("DRY RUN: Would create fallback quiz."))
                continue

            with transaction.atomic():
                if not quiz:
                    quiz = Quiz.objects.create(
                        course=course,
                        module=module,
                        generated_for=None,
                        title=f"{module.title} Mastery Check",
                        description=(
                            "Emergency fallback assessment based on this module's available content. "
                            "This quiz can be regenerated later using AI."
                        ),
                        category="practice",
                        pass_mark=70,
                        answers_at_end=True,
                        exam_paper=True,
                        draft=False,
                        generation_status="processing",
                        generation_message="Creating emergency fallback quiz.",
                        generation_started_at=timezone.now(),
                    )

                # Archive duplicate shared quizzes if any exist.
                Quiz.objects.filter(
                    module=module,
                    generated_for__isnull=True,
                    draft=False,
                ).exclude(pk=quiz.pk).update(
                    draft=True,
                    generation_message="Archived duplicate shared quiz during fallback generation.",
                )

                quiz.questions.all().delete()

                fallback_questions = build_fallback_questions(module)

                for order, item in enumerate(fallback_questions, start=1):
                    question = MCQuestion.objects.create(
                        quiz=quiz,
                        content=item["question"],
                        explanation=item["explanation"],
                        order=order,
                    )

                    for choice_index, choice_text in enumerate(item["choices"]):
                        Choice.objects.create(
                            question=question,
                            content=choice_text,
                            correct=choice_index == item["correct_index"],
                        )

                quiz.generation_status = "ready"
                quiz.ai_generated = False
                quiz.generation_message = (
                    "Emergency fallback quiz is ready. Regenerate later with AI for higher quality."
                )
                quiz.generation_completed_at = timezone.now()
                quiz.save(update_fields=[
                    "generation_status",
                    "generation_message",
                    "generation_completed_at",
                    "ai_generated",
                ])

                job.status = "completed"
                job.error = "Completed using emergency fallback quiz generation."
                job.completed_at = timezone.now()
                job.locked_at = None
                job.started_at = None
                job.save(update_fields=[
                    "status",
                    "error",
                    "completed_at",
                    "locked_at",
                    "started_at",
                    "updated_at",
                ])

            completed += 1
            self.stdout.write(self.style.SUCCESS(
                f"Fallback quiz ready: Quiz #{quiz.id} with {quiz.questions.count()} question(s)."
            ))

        self.stdout.write("")
        self.stdout.write("=" * 70)
        self.stdout.write(self.style.SUCCESS(f"Completed fallback quizzes: {completed}"))
        self.stdout.write(self.style.WARNING(f"Skipped: {skipped}"))
        self.stdout.write("Done.")


def build_fallback_questions(module):
    course_title = module.course.title
    module_title = module.title
    description = strip_tags(module.description or "")

    content_texts = []

    for content in module.contents.order_by("order", "id")[:8]:
        body = ""

        if content.content_type == "text":
            body = strip_tags(content.text_content or "")
        elif content.content_type == "link":
            body = content.external_link or ""
        elif content.content_type == "video":
            body = content.video_url or ""
        elif content.document:
            body = f"document resource {content.document.name}"

        if content.title:
            content_texts.append(strip_tags(content.title))

        if body:
            content_texts.append(body)

    combined = " ".join([course_title, module_title, description] + content_texts)
    clean = re.sub(r"\s+", " ", strip_tags(combined)).strip()

    summary = Truncator(clean or module_title).chars(220)
    terms = extract_terms(clean, module_title)

    t1 = terms[0]
    t2 = terms[1] if len(terms) > 1 else module_title
    t3 = terms[2] if len(terms) > 2 else course_title

    return [
        {
            "question": f"What is the main focus of {module_title}?",
            "choices": [
                f"Understanding key ideas and skills from {module_title}.",
                "Ignoring the module content and guessing answers.",
                "Studying topics unrelated to this course.",
                "Skipping the learning material completely.",
            ],
            "correct_index": 0,
            "explanation": f"This module belongs to {course_title} and focuses on its listed learning content.",
        },
        {
            "question": f"Why is {t1} important in this module?",
            "choices": [
                f"It is connected to the module's main learning material.",
                "It is unrelated to the course topic.",
                "It replaces the need to study the module.",
                "It is only useful outside this course.",
            ],
            "correct_index": 0,
            "explanation": f"The available module context connects {t1} to the lesson focus: {summary}",
        },
        {
            "question": f"How should a learner approach {module_title}?",
            "choices": [
                "Review the content carefully and connect ideas to practice.",
                "Memorize random words without understanding.",
                "Ignore examples and explanations.",
                "Focus only on unrelated outside topics.",
            ],
            "correct_index": 0,
            "explanation": "A mastery check expects understanding of the module content, not random memorization.",
        },
        {
            "question": f"Which statement best describes {t2}?",
            "choices": [
                f"It is part of the learning context for {module_title}.",
                "It has no connection to the module.",
                "It means the course has no learning goal.",
                "It should be avoided by the learner.",
            ],
            "correct_index": 0,
            "explanation": f"{t2} appears as part of the module's available course context.",
        },
        {
            "question": f"What should the learner be able to do after studying this module?",
            "choices": [
                f"Explain important ideas from {module_title} in their own words.",
                "Answer without reading the module content.",
                "Forget the relationship between lessons.",
                "Use only unrelated information.",
            ],
            "correct_index": 0,
            "explanation": f"The goal is to understand the module content and apply the key ideas from {course_title}.",
        },
    ]


def extract_terms(text, fallback):
    words = re.findall(r"\b[A-Za-zÀ-ÖØ-öø-ÿ][A-Za-zÀ-ÖØ-öø-ÿ0-9\-]{4,}\b", text or "")

    stopwords = {
        "module", "course", "lesson", "content", "student", "learn",
        "learning", "introduction", "mastery", "check", "moduli",
        "kozi", "utani", "katika", "mwanafunzi", "kujifunza",
        "module", "modules", "title", "description",
    }

    terms = []
    seen = set()

    for word in words:
        cleaned = word.strip(".,;:()[]{}\"'").strip()
        lower = cleaned.lower()

        if lower in stopwords:
            continue

        if lower in seen:
            continue

        seen.add(lower)
        terms.append(cleaned)

        if len(terms) >= 5:
            break

    if not terms:
        terms = [fallback]

    return terms
