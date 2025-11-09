import pytest
from jobs.api_integration import AjiraGraphQLClient
from types import SimpleNamespace
from django.utils import timezone

class DummyConfig:
    def __init__(self):
        self.additional_params = {}
        self.api_key = ''
        self.api_secret = ''

    def __getattr__(self, item):
        return None


def test_map_vacancy_to_job_basic():
    api_config = DummyConfig()
    client = AjiraGraphQLClient(api_config)
    vac = {
        'id': 123,
        'scheme': {
            'id': 1,
            'codeNo': 'PS/2025/001',
            'emp': { 'id': 99, 'name': 'Public Service' }
        },
        'openDate': '2025-11-01T00:00:00',
        'closeDate': '2025-11-30T23:59:59'
    }
    job = client._map_vacancy_to_job(vac)
    assert job['external_id'] == 'ajira:123'
    assert 'PS/2025/001' in job['title']
    assert job['company_name'] == 'Public Service'
    assert job['source'] == 'ajira'
    assert job['application_deadline'] is not None
