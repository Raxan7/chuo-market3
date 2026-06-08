import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Commerce.settings')
import django; django.setup()

from lms.models import Quiz

# Mark AI-generated quizzes
ai_count = Quiz.objects.filter(
    generation_status='ready',
    generation_message='Quiz is ready.',
).update(ai_generated=True)
print(f"Marked {ai_count} AI-generated quizzes")

# Mark fallback quizzes
fallback_count = Quiz.objects.filter(
    generation_status='ready',
    generation_message__contains='fallback',
).update(ai_generated=False)
print(f"Marked {fallback_count} fallback quizzes")

# Show summary
total = Quiz.objects.filter(module__isnull=False, generated_for__isnull=True, draft=False).count()
ai_total = Quiz.objects.filter(module__isnull=False, generated_for__isnull=True, draft=False, ai_generated=True).count()
non_ai = total - ai_total
print(f"\nTotal shared quizzes: {total}")
print(f"AI generated: {ai_total}")
print(f"Non-AI (fallback/manual): {non_ai}")
