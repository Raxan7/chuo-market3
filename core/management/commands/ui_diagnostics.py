from django.contrib.staticfiles import finders
from django.core.management.base import BaseCommand, CommandError
from django.template.loader import get_template
from django.urls import reverse


class Command(BaseCommand):
    help = 'Validate ChuoSmart UI routes, templates, themes, and uniquely-namespaced static assets.'

    ROUTES = (
        ('home', 'HOME'),
        ('for_business', 'FOR_BUSINESS'),
        ('ai_workforce_accelerator', 'AI_WORKFORCE_ACCELERATOR'),
        ('lms:course_list', 'COURSE_LIST'),
        ('lms:lms_home', 'LEARNING_HOME'),
    )
    TEMPLATES = ('app/base.html', 'app/home.html', 'app/for_business.html', 'app/ai_workforce_accelerator.html')
    ASSETS = (
        'chuosmart_v2/css/site.css',
        'chuosmart_v2/css/discovery.css',
        'chuosmart_v2/js/site.js',
        'chuosmart_v2/images/enterprise-team.webp',
        'chuosmart_v2/images/workshop.webp',
        'chuosmart_v2/images/governance.webp',
        'chuosmart_v2/images/outcomes-dashboard.webp',
    )

    def handle(self, *args, **options):
        errors = []
        self.stdout.write('=== ChuoSmart UI v2 diagnostics ===')

        for route, label in self.ROUTES:
            try:
                url = reverse(route)
            except Exception as exc:
                errors.append(f'Route {route}: {exc}')
            else:
                self.stdout.write(f'ROUTE_{label}={url}')

        for template_name in self.TEMPLATES:
            try:
                get_template(template_name)
            except Exception as exc:
                errors.append(f'Template {template_name}: {exc}')
            else:
                self.stdout.write(f'TEMPLATE_OK={template_name}')

        for asset in self.ASSETS:
            matches = finders.find(asset, all=True)
            if len(matches) != 1:
                errors.append(f'Static asset {asset} resolves {len(matches)} times: {matches}')
            else:
                self.stdout.write(f'STATIC_OK={asset}')

        css_path = finders.find('chuosmart_v2/css/site.css')
        js_path = finders.find('chuosmart_v2/js/site.js')
        if css_path and js_path:
            with open(css_path, encoding='utf-8') as handle:
                css = handle.read()
            with open(js_path, encoding='utf-8') as handle:
                javascript = handle.read()
            theme_contract = {
                'system': "chuosmart.theme" in javascript and "prefers-color-scheme: dark" in javascript,
                'light': 'html[data-cs-theme="light"]' in css,
                'dark': 'html[data-cs-theme="dark"]' in css,
                'midnight': 'html[data-cs-theme="midnight"]' in css,
            }
            for theme, healthy in theme_contract.items():
                if healthy:
                    self.stdout.write(f'THEME_OK={theme}')
                else:
                    errors.append(f'Theme contract incomplete: {theme}')

            contrast_contract = all(
                marker in css
                for marker in (
                    '--cs-action-bg:',
                    '--cs-info-bg:',
                    '--cs-info-text:',
                    '--cs-success-bg:',
                    '--cs-warning-bg:',
                    '--cs-danger-bg:',
                    '.alert-info',
                    '.alert-success',
                    '.alert-warning',
                    '.alert-danger',
                    '.badge.bg-warning.text-dark',
                    '.card-header.bg-light',
                )
            )
            if contrast_contract:
                self.stdout.write('THEME_CONTRAST_OK=semantic-components')
            else:
                errors.append('Theme contrast contract incomplete: semantic components')

        if errors:
            for error in errors:
                self.stderr.write(self.style.ERROR(error))
            raise CommandError(f'UI diagnostics failed with {len(errors)} issue(s).')

        self.stdout.write(self.style.SUCCESS('UI diagnostics passed: routes, templates, themes and v2 assets are healthy.'))
