"""
URL patterns for the LMS application
"""

from django.urls import path
from . import views

app_name = 'lms'

urlpatterns = [
    # Debug views - remove in production
    path('debug/upload/', views.debug_upload_view, name='debug_upload'),
    # Session management
    path('session-keep-alive/', views.session_keep_alive, name='session_keep_alive'),
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
    path('courses/<slug:slug>/', views.CourseAdvertisementView.as_view(), name='course_detail'),
    path('courses/<slug:slug>/direct/', views.CourseDetailView.as_view(), name='course_detail_direct'),
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
    path('courses/<slug:course_slug>/grade-students/', views.grade_students, name='grade_students'),
    
    # Instructor Request
    path('become-instructor/', views.request_instructor_role, name='request_instructor_role'),
    path('instructor-request-status/', views.instructor_request_status, name='instructor_request_status'),
    
    # Ad Exemption Management
    path('ad-exemption/toggle/<int:user_id>/', views.toggle_ad_exemption, name='toggle_ad_exemption'),
    
    # Payment Management
    path('courses/<slug:slug>/payment/', views.payment_form, name='payment_form'),
    path('courses/<slug:slug>/payment/pending/', views.payment_pending, name='payment_pending'),
    
    # Instructor payment methods
    path('instructor/payment-methods/', views.instructor_payment_methods, name='instructor_payment_methods'),
    path('instructor/payment-methods/add/', views.add_payment_method, name='add_payment_method'),
    path('instructor/payment-methods/<int:pk>/edit/', views.edit_payment_method, name='edit_payment_method'),
    path('instructor/payment-methods/<int:pk>/delete/', views.delete_payment_method, name='delete_payment_method'),
]
