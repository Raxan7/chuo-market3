from django.test import TestCase, Client
from django.urls import reverse
from chatbotapp.models import ChatMessage
import time

class SessionTestCase(TestCase):
    def setUp(self):
        self.client = Client()
