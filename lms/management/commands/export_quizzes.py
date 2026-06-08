import json
import logging

from datetime import datetime

from django.core.management.base import BaseCommand
from django.db import close_old_connections

from lms.models import Quiz

logger = logging.getLogger(__name__)


def safe_text(text):
    if isinstance(text, str):
        return text.encode('utf-8', errors='replace').decode('utf-8', errors='replace')
    return text


class Command(BaseCommand):
    help = "Export all module quizzes to a JSON file for production import."

    def add_arguments(self, parser):
        parser.add_argument("output_file", type=str, help="Path to output JSON file")
        parser.add_argument("--ai-only", action="store_true", help="Export only AI-generated quizzes")
        parser.add_argument("--minimal", action="store_true", help="Export only essential quiz data (no metadata flags)")

    def handle(self, *args, **options):
        output_file = options["output_file"]
        ai_only = options["ai_only"]
        minimal = options["minimal"]

        quizzes = Quiz.objects.filter(module__isnull=False, generated_for__isnull=True).select_related("course", "module").order_by("course__title", "module__order", "module__id")
        if ai_only:
            quizzes = quizzes.filter(ai_generated=True)

        total = quizzes.count()
        self.write(f"Exporting {total} quiz(es)...")
        self.write("")

        exported = []
        for quiz in quizzes.iterator():
            close_old_connections()

            questions_data = []
            for qst in quiz.questions.all().order_by("order"):
                qst_data = {
                    "content": qst.content,
                    "explanation": qst.explanation,
                    "order": qst.order,
                }

                if hasattr(qst, "mcquestion"):
                    mcq = qst.mcquestion
                    qst_data["type"] = "mcq"
                    qst_data["choice_order"] = mcq.choice_order
                    qst_data["choices"] = [
                        {"content": c.content, "correct": c.correct}
                        for c in mcq.choices.all()
                    ]
                elif hasattr(qst, "tf_question"):
                    tfq = qst.tf_question
                    qst_data["type"] = "tf"
                    qst_data["correct"] = tfq.correct
                elif hasattr(qst, "essay_question"):
                    eq = qst.essay_question
                    qst_data["type"] = "essay"
                    qst_data["answer_type"] = eq.answer_type
                else:
                    qst_data["type"] = "unknown"

                questions_data.append(qst_data)

            entry = {
                "module_id": quiz.module_id,
                "course_id": quiz.course_id,
                "quiz_id": quiz.id,
                "course_title": quiz.course.title,
                "module_title": quiz.module.title,
                "title": quiz.title,
                "slug": quiz.slug,
                "description": quiz.description,
                "category": quiz.category,
                "pass_mark": quiz.pass_mark,
                "draft": quiz.draft,
                "ai_generated": quiz.ai_generated,
                "questions": questions_data,
            }

            if not minimal:
                entry.update({
                    "random_order": quiz.random_order,
                    "answers_at_end": quiz.answers_at_end,
                    "exam_paper": quiz.exam_paper,
                    "single_attempt": quiz.single_attempt,
                    "generation_status": quiz.generation_status,
                    "generation_message": quiz.generation_message,
                    "due_date": quiz.due_date.isoformat() if quiz.due_date else None,
                })

            exported.append(entry)

        payload = {
            "version": 2,
            "export_date": datetime.now().isoformat(),
            "quiz_count": len(exported),
            "quizzes": exported,
        }

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)

        self.write("")
        self.write(f"Exported {len(exported)} quiz(es) to {output_file}", self.style.SUCCESS)

    def write(self, msg, style=None):
        msg = safe_text(msg)
        if style:
            self.stdout.write(style(msg))
        else:
            self.stdout.write(msg)
