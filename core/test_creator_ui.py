from django.contrib.auth.models import AnonymousUser, User
from django.test import RequestFactory, TestCase
from django.urls import reverse

from core.context_processors import creator_access
from jobs.models import UserJobApproval
from lms.models import InstructorRequest


class CreatorAccessContextTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def _context_for(self, user):
        request = self.factory.get('/')
        request.user = user
        return creator_access(request)

    def test_anonymous_user_has_no_creator_tools(self):
        context = self._context_for(AnonymousUser())
        self.assertFalse(context['can_post_jobs'])
        self.assertFalse(context['can_create_courses'])
        self.assertFalse(context['has_creator_tools'])

    def test_signed_in_user_gets_job_creator_access_before_approval(self):
        user = User.objects.create_user(username='job-poster', password='password12345')

        context = self._context_for(user)

        self.assertTrue(context['can_post_jobs'])
        self.assertFalse(context['can_create_courses'])
        self.assertTrue(context['has_creator_tools'])

    def test_approved_job_poster_keeps_job_creator_access(self):
        user = User.objects.create_user(username='approved-employer', password='password12345')
        UserJobApproval.objects.create(user=user, is_approved=True)

        context = self._context_for(user)

        self.assertTrue(context['can_post_jobs'])
        self.assertFalse(context['can_create_courses'])
        self.assertTrue(context['has_creator_tools'])

    def test_instructor_gets_course_creator_access(self):
        user = User.objects.create_user(username='course-instructor', password='password12345')
        user.lms_profile.role = 'instructor'
        user.lms_profile.save(update_fields=['role'])

        context = self._context_for(user)

        self.assertTrue(context['can_post_jobs'])
        self.assertTrue(context['can_create_courses'])
        self.assertTrue(context['can_use_instructor_dashboard'])
        self.assertTrue(context['has_creator_tools'])

    def test_lms_admin_can_create_courses_without_instructor_dashboard_link(self):
        user = User.objects.create_user(username='course-admin', password='password12345')
        user.lms_profile.role = 'admin'
        user.lms_profile.save(update_fields=['role'])

        context = self._context_for(user)

        self.assertTrue(context['can_post_jobs'])
        self.assertTrue(context['can_create_courses'])
        self.assertFalse(context['can_use_instructor_dashboard'])
        self.assertTrue(context['has_creator_tools'])

    def test_approved_legacy_instructor_request_is_exposed_immediately(self):
        user = User.objects.create_user(username='legacy-instructor', password='password12345')
        self.assertEqual(user.lms_profile.role, 'student')
        InstructorRequest.objects.create(
            user=user,
            reason='I can teach this topic.',
            qualifications='Relevant professional experience.',
            status='approved',
        )

        context = self._context_for(user)

        self.assertTrue(context['can_post_jobs'])
        self.assertTrue(context['can_create_courses'])
        self.assertTrue(context['can_use_instructor_dashboard'])
        self.assertTrue(context['has_creator_tools'])


class CreatorNavigationRegressionTests(TestCase):
    password = 'password12345'

    def _make_user(self, username, *, role='student', approved_jobs=False):
        user = User.objects.create_user(username=username, password=self.password)
        user.lms_profile.role = role
        user.lms_profile.save(update_fields=['role'])
        if approved_jobs:
            UserJobApproval.objects.create(user=user, is_approved=True)
        return user

    def test_approved_employer_sees_persistent_post_job_actions(self):
        user = self._make_user('nav-employer', approved_jobs=True)
        self.client.force_login(user)

        response = self.client.get(reverse('home'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="csMobileCreateMenuButton"')
        self.assertContains(response, 'data-creator-action="post-job"')
        self.assertContains(response, reverse('jobs:create_job'))
        self.assertNotContains(response, 'data-creator-action="create-course"')

    def test_instructor_sees_persistent_create_course_actions(self):
        user = self._make_user('nav-instructor', role='instructor')
        self.client.force_login(user)

        response = self.client.get(reverse('home'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="csMobileCreateMenuButton"')
        self.assertContains(response, 'data-creator-action="create-course"')
        self.assertContains(response, reverse('lms:course_create'))
        self.assertContains(response, reverse('lms:instructor_dashboard'))
        self.assertContains(response, 'data-creator-action="post-job"')

    def test_lms_admin_sees_course_create_on_catalogue(self):
        user = self._make_user('catalog-admin', role='admin')
        self.client.force_login(user)

        response = self.client.get(reverse('lms:course_list'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Create New Course')
        self.assertContains(response, reverse('lms:course_create'))

    def test_approved_employer_sees_post_job_on_job_catalogue(self):
        user = self._make_user('catalog-employer', approved_jobs=True)
        self.client.force_login(user)

        response = self.client.get(reverse('jobs:job_list'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-creator-action="post-job"')
        self.assertContains(response, 'Post a Job')

    def test_dual_creator_sees_dashboard_creator_panel_with_both_actions(self):
        user = self._make_user('dual-creator', role='instructor', approved_jobs=True)
        self.client.force_login(user)

        response = self.client.get(reverse('user_dashboard'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="creator-tools"')
        self.assertContains(response, 'Post a job')
        self.assertContains(response, 'Create a course')
        self.assertContains(response, reverse('jobs:create_job'))
        self.assertContains(response, reverse('lms:course_create'))

    def test_regular_signed_in_user_gets_job_post_shortcut_but_not_course(self):
        user = self._make_user('regular-student')
        self.client.force_login(user)

        response = self.client.get(reverse('home'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="csMobileCreateMenuButton"')
        self.assertContains(response, 'data-creator-action="post-job"')
        self.assertNotContains(response, 'data-creator-action="create-course"')
