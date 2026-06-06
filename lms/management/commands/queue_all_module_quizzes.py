from django.core.management.base import BaseCommand
from lms.models import CourseModule, Course
from lms.ai_assessments import queue_module_assessment_generation

class Command(BaseCommand):
    help = 'Queues AI quiz generation for all existing modules'

    def add_arguments(self, parser):
        parser.add_argument('--course-id', type=int)
        parser.add_argument('--force', action='store_true')
        parser.add_argument('--question-count', type=int, default=5)

    def handle(self, *args, **options):
        modules = CourseModule.objects.filter(skip_assessment=False)
        if options['course_id']:
            modules = modules.filter(course_id=options['course_id'])
        
        force = options['force']
        count = options['question_count']
        
        queued = 0
        skipped = 0
        
        for module in modules:
            # Check if it already has a ready quiz
            has_ready = module.quizzes.filter(
                generated_for__isnull=True, 
                draft=False, 
                generation_status='ready'
            ).exists()
            
            if has_ready and not force:
                skipped += 1
                continue
            
            queue_module_assessment_generation(module, question_count=count, force=force)
            queued += 1
        
        self.stdout.write(f"Done. Queued: {queued}, Skipped: {skipped}")