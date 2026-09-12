import os
import subprocess
import sys
from pathlib import Path

from django.test import SimpleTestCase


PROJECT_ROOT = Path(__file__).resolve().parent.parent


class RenderDeploymentContractTests(SimpleTestCase):
    def test_optional_docker_files_are_present(self):
        expected = (
            "Dockerfile",
            ".dockerignore",
            "render.yaml",
            "deploy/render/start.sh",
            "Commerce/settings/render.py",
        )
        for relative in expected:
            with self.subTest(path=relative):
                self.assertTrue((PROJECT_ROOT / relative).is_file(), relative)

    def test_dockerfile_uses_render_only_startup(self):
        dockerfile = (PROJECT_ROOT / "Dockerfile").read_text()
        self.assertIn("FROM python:3.12-slim-bookworm", dockerfile)
        self.assertIn("DJANGO_ENV=render", dockerfile)
        self.assertIn('CMD ["/app/deploy/render/start.sh"]', dockerfile)

    def test_render_blueprint_uses_isolated_database(self):
        blueprint = (PROJECT_ROOT / "render.yaml").read_text()
        self.assertIn("runtime: docker", blueprint)
        self.assertIn("chuosmart-prototype-db", blueprint)
        self.assertIn("property: connectionString", blueprint)
        self.assertNotIn("DB_HOST", blueprint)
        self.assertNotIn("chuosmart.com", blueprint)

    def test_render_settings_boot_independently(self):
        env = os.environ.copy()
        env.update(
            {
                "DJANGO_ENV": "render",
                "SECRET_KEY": "render-contract-test-only",
                "DATABASE_URL": "sqlite:////tmp/chuosmart-render-contract.sqlite3",
                "RENDER_ENABLE_OUTBOUND_EMAIL": "false",
            }
        )
        env.pop("DJANGO_SETTINGS_MODULE", None)

        result = subprocess.run(
            [sys.executable, "manage.py", "render_diagnostics"],
            cwd=PROJECT_ROOT,
            env=env,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        self.assertEqual(
            result.returncode,
            0,
            msg=f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}",
        )
        self.assertIn("Render diagnostics passed", result.stdout)
