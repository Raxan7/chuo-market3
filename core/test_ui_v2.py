from django.contrib.staticfiles import finders
from django.test import RequestFactory, TestCase
from django.urls import reverse

from core.context_processors import site_ad_settings
from core.sitemaps import StaticViewSitemap


class ChuoSmartUIV2RoutingTests(TestCase):
    def test_business_landing_renders_without_ads(self):
        response = self.client.get(reverse('for_business'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Build AI capability your organization can actually use.')
        self.assertContains(response, 'AI Workforce Accelerator')
        self.assertNotContains(response, 'pagead2.googlesyndication.com')

    def test_accelerator_page_renders_flagship_offer(self):
        response = self.client.get(reverse('ai_workforce_accelerator'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'AI Workforce Accelerator')
        self.assertContains(response, 'TZS 50M')
        self.assertContains(response, '16+ common practical labs')
        self.assertNotContains(response, 'pagead2.googlesyndication.com')

    def test_home_is_premium_front_door_without_ads(self):
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Build a future-ready workforce')
        self.assertContains(response, 'Explore ChuoSmart for Business')
        self.assertNotContains(response, 'pagead2.googlesyndication.com')

    def test_home_keeps_individual_learning_first_class(self):
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'For individuals')
        self.assertContains(response, 'Practical courses are still at the heart of ChuoSmart.')
        self.assertContains(response, reverse('lms:course_list'))
        self.assertContains(response, '?pricing=free')
        self.assertContains(response, reverse('lms:lms_home'))

    def test_normal_course_catalogue_route_still_works(self):
        response = self.client.get(reverse('lms:course_list'))
        self.assertEqual(response.status_code, 200)

    def test_global_navigation_exposes_individual_learning(self):
        response = self.client.get(reverse('home'))
        self.assertContains(response, 'For Individuals')
        self.assertContains(response, '<strong>Courses</strong>', html=True)
        self.assertContains(response, 'Free Courses')

    def test_global_shell_exposes_multi_theme_controls(self):
        response = self.client.get(reverse('home'))
        self.assertContains(response, 'id="csThemeMenuButton"')
        for theme in ('system', 'light', 'dark', 'midnight'):
            self.assertContains(response, f'data-cs-theme-choice="{theme}"')

    def test_theme_bootstrap_is_rendered_before_styles(self):
        response = self.client.get(reverse('home'))
        html = response.content.decode('utf-8')
        bootstrap_pos = html.find("chuosmart.theme")
        stylesheet_pos = html.find("chuosmart_v2/css/site.css")
        self.assertGreaterEqual(bootstrap_pos, 0)
        self.assertGreater(stylesheet_pos, bootstrap_pos)

    def test_static_sitemap_includes_business_routes(self):
        items = StaticViewSitemap().items()
        self.assertIn('for_business', items)
        self.assertIn('ai_workforce_accelerator', items)


class ChuoSmartUIV2ContextTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_home_is_premium_and_ad_free(self):
        context = site_ad_settings(self.factory.get('/'))
        self.assertTrue(context['premium_surface'])
        self.assertFalse(context['business_surface'])
        self.assertFalse(context['ads_allowed'])

    def test_business_surface_is_premium_and_ad_free(self):
        context = site_ad_settings(self.factory.get('/for-business/'))
        self.assertTrue(context['premium_surface'])
        self.assertTrue(context['business_surface'])
        self.assertFalse(context['ads_allowed'])

    def test_marketplace_remains_non_premium_surface(self):
        context = site_ad_settings(self.factory.get('/marketplace/'))
        self.assertFalse(context['premium_surface'])
        self.assertFalse(context['business_surface'])


class ChuoSmartUIV2StaticTests(TestCase):
    def test_v2_assets_have_unique_static_paths(self):
        assets = [
            'chuosmart_v2/css/site.css',
            'chuosmart_v2/js/site.js',
            'chuosmart_v2/images/enterprise-team.webp',
            'chuosmart_v2/images/workshop.webp',
            'chuosmart_v2/images/governance.webp',
            'chuosmart_v2/images/outcomes-dashboard.webp',
        ]
        for asset in assets:
            matches = finders.find(asset, all=True)
            self.assertEqual(len(matches), 1, f'{asset} should resolve exactly once, found: {matches}')


    def test_v2_theme_assets_define_all_supported_themes(self):
        css_path = finders.find('chuosmart_v2/css/site.css')
        js_path = finders.find('chuosmart_v2/js/site.js')
        self.assertTrue(css_path)
        self.assertTrue(js_path)

        with open(css_path, encoding='utf-8') as handle:
            css = handle.read()
        with open(js_path, encoding='utf-8') as handle:
            javascript = handle.read()

        self.assertIn('html[data-cs-theme="dark"]', css)
        self.assertIn('html[data-cs-theme="midnight"]', css)
        self.assertIn("chuosmart.theme", javascript)
        self.assertIn("prefers-color-scheme: dark", javascript)
        self.assertIn("chuosmart:themechange", javascript)
