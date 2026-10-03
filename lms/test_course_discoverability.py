"""Regression tests for instructors losing sight of courses they just created.

Reports came in that a course upload "completes without error" but the course
cannot be found when searching the public course list by its title.

Sticky filters silently hid a title match. The filter panel on the public
list is a collapsed accordion, and its selects are repopulated from
``current_filters``, so a filter the instructor set once kept applying to
every later search. A stale ``level=3`` excluded a course that is not
Level 3, and because the search box still showed the title it read as a
broken search. The only recovery link was a bare course-list URL with no
query string, which wiped the filter *and* the instructor's query at once.

A second suspected defect turned out not to be real. ``Course.code`` is
``unique=True`` and is not required for general courses, which looked like
it would persist ``''`` and collide on the second general course. Django's
own field coercion stores it as ``NULL`` (``CharField`` with ``blank=True``
normalises empty values before they reach the database), so those tests now
pass without any change. They are kept because they pin that behaviour: it is
load-bearing, and it is not obvious from the model declaration.

The search behaviour is asserted against the real view, because the whole
defect lives in the interaction between the view's filter ordering and the
template's hidden state -- neither is visible from the queryset alone.
"""

import re

from django.contrib.auth.models import User
from django.db import IntegrityError, transaction
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from .forms import CourseForm
from .models import Course, LMSProfile


@override_settings(
    DEBUG=True,
    STORAGES={
        'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
        'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
    },
)
class StickyFilterSearchTests(TestCase):
    """A title search must find a course regardless of unrelated filters."""

    def setUp(self):
        # A course that is deliberately NOT Level 3.
        self.course = Course.objects.create(
            title='Introduction to Marine Biology',
            course_type='general',
            code=None,
            summary='A general course about coral reefs.',
            level=None,
            semester=None,
        )

    def _search(self, **params):
        response = self.client.get(reverse('lms:course_list'), params)
        self.assertEqual(response.status_code, 200)
        return list(response.context['courses'])

    def test_title_search_finds_the_course(self):
        found = self._search(q='Marine Biology')
        self.assertIn(
            self.course,
            found,
            'searching the exact course title must return the course',
        )

    def test_stale_level_filter_does_not_hide_a_title_match(self):
        """The reported bug: a leftover level filter silently drops results."""
        # The instructor set level=3 earlier and searches by title.
        found = self._search(q='Marine Biology', level='3')
        self.assertIn(
            self.course,
            found,
            'a title match must survive an unrelated stale level filter; '
            'otherwise the instructor sees "No Courses Found" for a course '
            'that was saved successfully',
        )

    def test_stale_filters_are_reported_in_the_empty_state(self):
        """When filters legitimately exclude everything, say which ones.

        Browsing without a search term, since an explicit search deliberately
        ignores the browse filters.
        """
        response = self.client.get(
            reverse('lms:course_list'),
            {'level': '1', 'program': '999999'},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(list(response.context['courses']), [])
        body = response.content.decode()
        self.assertIn(
            'data-testid="empty-state-filters"',
            body,
            'the empty state must name the active filters, otherwise the '
            'instructor cannot tell why their own course is missing',
        )
        # Level is one of the filters that produced the empty result.
        self.assertIn('Level 1', body)

    def test_search_ignores_filters_and_says_so(self):
        """A title search must not be narrowed by leftover filters."""
        response = self.client.get(
            reverse('lms:course_list'),
            {'q': 'Marine Biology', 'level': '3'},
        )
        self.assertIn(self.course, list(response.context['courses']))
        # And the panel must not silently look broken by ignoring the selects.
        self.assertTrue(response.context['search_overrides_filters'])
        self.assertIn(
            'Searching all courses',
            response.content.decode(),
            'the page should explain that a search is not narrowed by filters',
        )

    def test_recovery_link_preserves_the_search_term(self):
        """Clearing filters must not also throw away the instructor's query."""
        response = self.client.get(
            reverse('lms:course_list'),
            {'q': 'Marine Biology', 'level': '3'},
        )
        body = response.content.decode()
        # There must be a link that drops the filters but keeps ?q=..., so
        # recovery does not dump the instructor back into an unfiltered list of
        # 100+ courses with an empty search box.
        search_links = [
            href for href in re.findall(r'href="([^"]*)"', body)
            if 'q=' in href
        ]
        self.assertTrue(
            search_links,
            'expected a link that clears filters while keeping the search term',
        )
        self.assertTrue(
            any('level=3' not in href for href in search_links),
            f'expected a filter-clearing link that keeps q but drops level, got {search_links}',
        )

    def test_active_filters_are_visible_without_opening_the_panel(self):
        """Collapsed filters must still be discoverable."""
        response = self.client.get(
            reverse('lms:course_list'),
            {'q': 'Marine Biology', 'level': '3', 'semester': 'First'},
        )
        body = response.content.decode()
        self.assertIn(
            'Filter by:',
            body,
            'active filters must be shown as removable chips; they are '
            'otherwise invisible inside a collapsed accordion',
        )


@override_settings(
    DEBUG=True,
    STORAGES={
        'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
        'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
    },
)
class CourseCodeUniquenessTests(TestCase):
    """``code`` is unique, so a blank value must be stored as NULL, not ''."""

    def setUp(self):
        self.user = User.objects.create_user(username='inst', password='pw')
        # The User post_save signal already created this profile with the
        # default 'student' role, so get_or_create would hand that back.
        # Course.instructors is limited to role='instructor', so promote it.
        self.profile = LMSProfile.objects.get(user=self.user)
        self.profile.role = 'instructor'
        self.profile.save()

    def _general_course_payload(self, title):
        return {
            'title': title,
            'course_type': 'general',
            'code': '',
            'credit': 3,
            'summary': 'summary',
            'content': 'content',
            'program': '',
            'level': '',
            'year': 1,
            'semester': '',
            'is_elective': False,
            'is_free': True,
            'price': '0',
            # `image` is optional and deliberately omitted so this same payload
            # can be posted to the view (None is not encodable as POST data).
            # `instructors` is a required field on the form, so the payload has
            # to satisfy it to reach the code-normalisation behaviour under test.
            'instructors': [str(self.profile.pk)],
        }

    def test_form_normalises_blank_code_to_none(self):
        form = CourseForm(data=self._general_course_payload('Coral Reefs'))
        self.assertTrue(form.is_valid(), form.errors)
        self.assertIsNone(
            form.cleaned_data['code'],
            'a blank code must be normalised to NULL: MySQL treats the empty '
            'string as a real value under UNIQUE, so storing it literally '
            'would let only one code-less course exist',
        )

    def test_two_general_courses_without_codes_both_save(self):
        """Repeated code-less courses must both persist.

        This was the scenario that looked like a live IntegrityError. It
        passes today because the form normalises the blank code to NULL, so
        there is no collision for MySQL's UNIQUE index to reject.
        """
        payloads = [
            self._general_course_payload('Coral Reefs'),
            self._general_course_payload('Deep Sea Trenches'),
        ]
        created = []
        for payload in payloads:
            form = CourseForm(data=payload)
            self.assertTrue(form.is_valid(), form.errors)
            with transaction.atomic():
                created.append(form.save())
        self.assertEqual(len(created), 2)
        for course in created:
            self.assertIsNone(course.code)

    def test_view_creates_two_general_courses_without_codes(self):
        """End-to-end through the real create view an instructor uses."""
        self.client.force_login(self.user)
        for title in ('Coral Reefs', 'Deep Sea Trenches'):
            response = self.client.post(
                reverse('lms:course_create'), self._general_course_payload(title)
            )
            self.assertEqual(
                response.status_code, 302,
                f'creating {title!r} should not error',
            )
        self.assertEqual(
            Course.objects.filter(title__in=['Coral Reefs', 'Deep Sea Trenches']).count(),
            2,
            'both general courses without a code must be persisted',
        )

    def test_explicit_duplicate_codes_still_rejected(self):
        """The uniqueness guarantee itself must survive the normalisation."""
        Course.objects.create(title='First', code='CS101')
        form = CourseForm(data={
            'title': 'Second', 'course_type': 'university', 'code': 'CS101',
            'credit': 3, 'program': '', 'level': '', 'year': 1,
            'semester': '', 'is_elective': False, 'is_free': True,
            'price': '0', 'image': None,
        })
        # university courses also require the academic fields, so this is
        # invalid on those grounds -- the point is that code is not silently
        # dropped to NULL to dodge the constraint.
        self.assertFalse(form.is_valid())
        self.assertIn('code', form.errors)

    def test_blank_code_row_does_not_block_a_later_blank_code_row(self):
        """A NULL stored directly in the DB must not collide either."""
        Course.objects.create(title='Alpha', code=None)
        Course.objects.create(title='Beta', code=None)
        self.assertEqual(
            Course.objects.filter(code__isnull=True).count(),
            2,
            'NULL codes must be storable repeatedly',
        )
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Course.objects.create(title='Gamma', code='DUPLICATE')
                Course.objects.create(title='Delta', code='DUPLICATE')


@override_settings(
    DEBUG=True,
    STORAGES={
        'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
        'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
    },
)
class InstructorCourseVisibilityTests(TestCase):
    """An instructor needs to confirm their own course exists.

    The public list mixes every instructor's courses together and the
    instructor dashboard had no search at all, so with 100+ courses there was
    no way to answer "did my course save?" without browsing.
    """

    def setUp(self):
        self.user = User.objects.create_user(username='inst', password='pw')
        self.profile = LMSProfile.objects.get(user=self.user)
        self.profile.role = 'instructor'
        self.profile.save()
        self.client.force_login(self.user)

        self.mine = Course.objects.create(
            title='Introduction to Marine Biology', code='MB101',
            summary='coral reefs',
        )
        self.mine.instructors.add(self.profile)

    def test_my_courses_lists_the_instructors_course(self):
        response = self.client.get(reverse('lms:instructor_course_list'))
        self.assertEqual(response.status_code, 200)
        self.assertIn(self.mine, list(response.context['my_courses']))
        # Assert on the rendered page too: the card is pulled in as a template
        # include, so a context-only check would not catch breakage there.
        self.assertIn(
            'Introduction to Marine Biology',
            response.content.decode(),
            'the course must actually render on the page, not just be in context',
        )

    def test_my_courses_search_finds_by_title(self):
        response = self.client.get(
            reverse('lms:instructor_course_list'), {'q': 'Marine Biology'},
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(self.mine, list(response.context['my_courses']))

    def test_my_courses_excludes_other_instructors_courses(self):
        other = User.objects.create_user(username='other', password='pw')
        other_profile = LMSProfile.objects.get(user=other)
        other_profile.role = 'instructor'
        other_profile.save()
        theirs = Course.objects.create(title='Someone Elses Course', code='OTH1')
        theirs.instructors.add(other_profile)

        response = self.client.get(reverse('lms:instructor_course_list'))
        self.assertNotIn(theirs, list(response.context['my_courses']))

    def test_my_courses_orders_by_recency(self):
        later = Course.objects.create(title='Created Second')
        later.instructors.add(self.profile)
        response = self.client.get(reverse('lms:instructor_course_list'))
        titles = [c.title for c in response.context['my_courses']]
        self.assertEqual(
            titles,
            ['Created Second', 'Introduction to Marine Biology'],
            'an explicit ordering is required; the queryset was previously '
            'unordered so a new course had no guaranteed position',
        )

    def test_my_courses_requires_instructor(self):
        student = User.objects.create_user(username='stu', password='pw')
        client = Client()
        client.force_login(student)
        response = client.get(reverse('lms:instructor_course_list'))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response.url, reverse('lms:lms_home'),
            'a non-instructor must not be able to list teaching courses',
        )

    def test_dashboard_course_search(self):
        response = self.client.get(
            reverse('lms:instructor_dashboard'), {'course_q': 'Marine'},
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(self.mine, list(response.context['my_courses']))
        body = response.content.decode()
        self.assertIn('Introduction to Marine Biology', body)
        self.assertIn(
            'name="course_q"',
            body,
            'the dashboard search input must actually render',
        )

    def test_dashboard_search_does_not_break_stats(self):
        """The stats aggregates must still cover every course, not just matches.

        ``teaching_courses`` drives quiz stats, completion stats and the
        incomplete-course count. Filtering it to the search results would
        silently zero out those numbers, so the dashboard keeps a separate
        display queryset.
        """
        other_course = Course.objects.create(title='Another Course')
        other_course.instructors.add(self.profile)

        response = self.client.get(
            reverse('lms:instructor_dashboard'), {'course_q': 'Marine'},
        )
        self.assertEqual(
            [c.title for c in response.context['my_courses']],
            ['Introduction to Marine Biology'],
            'the display panel should honour the search',
        )
        self.assertEqual(
            response.context['total_teaching_courses'], 2,
            'the total should still count every teaching course',
        )
        self.assertEqual(
            response.context['teaching_courses'].count(), 2,
            'the stats queryset must remain unfiltered',
        )
