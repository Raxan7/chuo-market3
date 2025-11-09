from django.urls import path
from . import views

app_name = 'jobs'

urlpatterns = [
    # Public job views
    path('', views.jobs_home, name='home'),
    path('jobs/', views.job_list, name='job_list'),
    path('job/<int:job_id>/', views.job_detail, name='job_detail'),
    path('job/<int:job_id>/apply/', views.apply_for_job, name='apply_for_job'),
    path('job/<int:job_id>/application-submitted/', views.application_submitted, name='application_submitted'),
    
    # Bookmarking
    path('job/<int:job_id>/save/', views.save_job, name='save_job'),
    path('job/<int:job_id>/unsave/', views.remove_saved_job, name='remove_saved_job'),
    path('saved-jobs/', views.saved_jobs, name='saved_jobs'),
    
    # User applications
    path('my-applications/', views.my_applications, name='my_applications'),
    
    # Company management
    path('my-companies/', views.my_companies, name='my_companies'),
    path('company/create/', views.create_company, name='create_company'),
    path('company/<int:company_id>/edit/', views.edit_company, name='edit_company'),
    path('company/<int:company_id>/delete/', views.delete_company, name='delete_company'),
    path('company/<int:company_id>/dashboard/', views.company_dashboard, name='company_dashboard'),
    path('company/<int:company_id>/verify/', views.request_company_verification, name='request_verification'),
    
    # Job management
    path('my-jobs/', views.my_jobs, name='my_jobs'),
    path('job/create/', views.create_job, name='create_job'),
    path('job/<int:job_id>/edit/', views.edit_job, name='edit_job'),
    path('job/<int:job_id>/delete/', views.delete_job, name='delete_job'),
    path('job/<int:job_id>/applications/', views.job_applications, name='job_applications'),
    
    # Application management
    path('application/<int:application_id>/', views.application_detail, name='application_detail'),
    
    # User preferences
    path('preferences/', views.job_preferences, name='job_preferences'),
    # Maintenance endpoint for scheduled fetch/deactivate (used by uptime robot)
    path('update-jobs/', views.maintenance_update_jobs, name='maintenance_update_jobs'),
]
