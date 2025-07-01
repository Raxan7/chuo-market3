"""
URL patterns for the LMS application
"""

from django.urls import path
from . import views

app_name = 'lms'

urlpatterns = [
    # Home and dashboard
    path('', views.lms_home, name='lms_home'),
    path('student-dashboard/', views.student_dashboard, name='student_dashboard'),
    path('instructor-dashboard/', views.instructor_dashboard, name='instructor_dashboard'),
    
    # Programs
    path('programs/', views.ProgramListView.as_view(), name='program_list'),
    path('programs/<int:pk>/', views.ProgramDetailView.as_view(), name='program_detail'),
    
    # Courses
    path('courses/', views.CourseListView.as_view(), name='course_list'),
    path('courses/create/', views.CourseCreateView.as_view(), name='course_create'),
    path('courses/<slug:slug>/', views.CourseDetailView.as_view(), name='course_detail'),
    path('courses/<slug:slug>/update/', views.CourseUpdateView.as_view(), name='course_update'),
    path('courses/<slug:slug>/enroll/', views.enroll_course, name='enroll_course'),
    path('courses/<slug:slug>/unenroll/', views.unenroll_course, name='unenroll_course'),
    
    # Course modules
    path('courses/<slug:course_slug>/modules/create/', 
         views.CourseModuleCreateView.as_view(), name='module_create'),
    path('courses/<slug:course_slug>/modules/<int:module_id>/update/', 
         views.CourseModuleUpdateView.as_view(), name='module_update'),
    
    # Course content
    path('courses/<slug:course_slug>/modules/<int:module_id>/content/create/', 
         views.CourseContentCreateView.as_view(), name='content_create'),
    path('courses/<slug:course_slug>/content/<int:content_id>/update/', 
         views.CourseContentUpdateView.as_view(), name='content_update'),
    path('courses/<slug:course_slug>/content/<int:content_id>/', 
         views.course_content_detail, name='content_detail'),
    
    # Quizzes
    path('courses/<slug:course_slug>/quizzes/create/', 
         views.QuizCreateView.as_view(), name='quiz_create'),
    path('courses/<slug:course_slug>/modules/<int:module_id>/quizzes/create/', 
         views.QuizCreateView.as_view(), name='quiz_create_in_module'),
    path('quizzes/<slug:slug>/', views.QuizDetailView.as_view(), name='quiz_detail'),
    path('quizzes/<slug:slug>/start/', views.start_quiz, name='start_quiz'),
    path('quiz/<int:quiz_id>/taker/<int:quiz_taker_id>/question/<int:question_number>/', 
         views.quiz_question, name='quiz_question'),
    path('quiz-taker/<int:quiz_taker_id>/complete/', 
         views.complete_quiz, name='complete_quiz'),
    path('quiz-taker/<int:quiz_taker_id>/results/', 
         views.quiz_results, name='quiz_results'),
    
    # Quiz questions
    path('quiz/<int:quiz_id>/add-mc-question/', 
         views.add_mc_question, name='add_mc_question'),
    path('quiz/<int:quiz_id>/add-tf-question/', 
         views.add_tf_question, name='add_tf_question'),
    path('quiz/<int:quiz_id>/add-essay-question/', 
         views.add_essay_question, name='add_essay_question'),
    
    # Grades
    path('grades/', views.GradeListView.as_view(), name='grade_list'),
    path('courses/<slug:course_slug>/grade-students/', 
         views.grade_students, name='grade_students'),
]
