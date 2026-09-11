from django.contrib.staticfiles import finders
from django.core.management.base import BaseCommand, CommandError
from django.template.loader import get_template
from django.urls import reverse


class Command(BaseCommand):
    help = 'Validate Patch 14 UI routes, templates, and uniquely-namespaced static assets.'

    ROUTES = ('home', 'for_business', 'ai_workforce_accelerator')
    TEMPLATES = ('app/base.html', 'app/home.html', 'app/for_business.html', 'app/ai_workforce_accelerator.html')
    ASSETS = (
        'chuosmart_v2/css/site.css',
        'chuosmart_v2/js/site.js',
        'chuosmart_v2/images/enterprise-team.webp',
        'chuosmart_v2/images/workshop.webp',
        'chuosmart_v2/images/governance.webp',
        'chuosmart_v2/images/outcomes-dashboard.webp',
    )

    def handle(self, *args, **options):
        errors = []
        self.stdout.write('=== ChuoSmart UI v2 diagnostics ===')

        for route in self.ROUTES:
            try:
                url = reverse(route)
            except Exception as exc:
                errors.append(f'Route {route}: {exc}')
            else:
                self.stdout.write(f'ROUTE_{route.upper()}={url}')

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

        if errors:
            for error in errors:
                self.stderr.write(self.style.ERROR(error))
            raise CommandError(f'UI diagnostics failed with {len(errors)} issue(s).')

        self.stdout.write(self.style.SUCCESS('UI diagnostics passed: routes, templates and v2 assets are healthy.'))
