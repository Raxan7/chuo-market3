import json
import logging
import sys

from django.core.management.base import BaseCommand
from django.db import transaction, close_old_connections

from lms.models import CourseModule, Quiz, MCQuestion, TF_Question, Essay_Question, Choice

logger = logging.getLogger(__name__)


def safe_text(text):
    if isinstance(text, str):
        return text.encode('utf-8', errors='replace').decode('utf-8', errors='replace')
    return text


class Command(BaseCommand):
    help = "Import quizzes from a JSON file. Matches by module_id and replaces questions safely."

    def add_arguments(self, parser):
        parser.add_argument("input_file", type=str, help="Path to JSON file exported by export_quizzes")
        parser.add_argument("--create-missing", action="store_true", help="Create new quizzes if no existing quiz is found for a module")

    def handle(self, *args, **options):
        input_file = options["input_file"]
        create_missing = options["create_missing"]

        with open(input_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        quizzes_data = data.get("quizzes", [])
        total = len(quizzes_data)
        self.write(f"Importing {total} quiz(es) from {input_file}...")
        self.write("")

        stats = {"imported": 0, "created": 0, "updated": 0, "skipped": 0, "errors": 0}

        for entry in quizzes_data:
            close_old_connections()
            module_id = entry["module_id"]

            try:
                module = CourseModule.objects.get(id=module_id)
            except CourseModule.DoesNotExist:
                self.write(f"  [SKIP] Module #{module_id} not found in database", self.style.WARNING)
                stats["skipped"] += 1
                continue

            with transaction.atomic():
                try:
                    quiz = Quiz.objects.select_for_update().get(
                        module=module,
                        generated_for__isnull=True,
                    )
                    existing = True
                except Quiz.DoesNotExist:
                    if not create_missing:
                        self.write(f"  [SKIP] No quiz for Module #{module_id} ({module.title}) and --create-missing not set", self.style.WARNING)
                        stats["skipped"] += 1
                        continue
                    quiz = Quiz(
                        module=module,
                        course_id=module.course_id,
                        draft=entry.get("draft", False),
                    )
                    existing = False

                # Update quiz fields
                quiz.title = entry.get("title", quiz.title)
                quiz.description = entry.get("description", "")
                quiz.category = entry.get("category", "")
                quiz.pass_mark = entry.get("pass_mark", 70)
                quiz.random_order = entry.get("random_order", False)
                quiz.answers_at_end = entry.get("answers_at_end", False)
                quiz.exam_paper = entry.get("exam_paper", False)
                quiz.single_attempt = entry.get("single_attempt", False)
                quiz.ai_generated = entry.get("ai_generated", True)
                quiz.generation_status = entry.get("generation_status", "ready")
                quiz.generation_message = entry.get("generation_message", "")
                if not quiz.slug:
                    quiz.slug = ""

                quiz.save()

                # Delete old questions (cascades to MCQuestion/TF_Question/Choice)
                quiz.questions.all().delete()

                # Recreate questions from JSON
                for qst_data in entry.get("questions", []):
                    base_kwargs = {
                        "quiz": quiz,
                        "content": qst_data["content"],
                        "explanation": qst_data.get("explanation", ""),
                        "order": qst_data.get("order", 0),
                    }

                    q_type = qst_data.get("type")

                    if q_type == "mcq":
                        question = MCQuestion.objects.create(
                            **base_kwargs,
                            choice_order=qst_data.get("choice_order", "content"),
                        )
                        for c_data in qst_data.get("choices", []):
                            Choice.objects.create(
                                question=question,
                                content=c_data["content"],
                                correct=c_data.get("correct", False),
                            )
                    elif q_type == "tf":
                        TF_Question.objects.create(
                            **base_kwargs,
                            correct=qst_data.get("correct", False),
                        )
                    elif q_type == "essay":
                        Essay_Question.objects.create(
                            **base_kwargs,
                            answer_type=qst_data.get("answer_type", "text"),
                        )
                    else:
                        self.write(f"    Unknown question type '{q_type}', skipping question...", self.style.WARNING)

                action = "Created" if not existing else "Updated"
                stats["imported"] += 1
                if not existing:
                    stats["created"] += 1
                else:
                    stats["updated"] += 1
                self.write(f"  [{action}] Quiz #{quiz.id} for Module #{module_id} ({module.title})", self.style.SUCCESS)

        self.write("")
        self.write("=" * 60)
        self.write(f"Done. {stats['imported']} imported ({stats['created']} new, {stats['updated']} updated), {stats['skipped']} skipped, {stats['errors']} errors", self.style.SUCCESS)

    def write(self, msg, style=None):
        msg = safe_text(msg)
        if style:
            self.stdout.write(style(msg))
        else:
            self.stdout.write(msg)
