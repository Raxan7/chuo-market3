from decimal import Decimal

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import SimpleTestCase, TestCase, override_settings

from .media import (
    soundcloud_embed_url,
    youtube_embed_url,
    youtube_video_id,
)
from .models import Course, CoursePayment
from .pricing import (
    FREE_CERTIFICATE_PRICE,
    PricingError,
    calculate_pricing,
    full_course_payment_includes_certificate,
    validate_component_price,
)


class PricingEngineTests(SimpleTestCase):
    def test_50000_package_with_10_modules(self):
        plan = calculate_pricing(
            Decimal("50000"),
            10,
            is_free=False,
        )

        self.assertEqual(
            plan.certificate_price,
            Decimal("15000"),
        )
        self.assertEqual(
            plan.module_prices,
            tuple(Decimal("3500") for _ in range(10)),
        )
        self.assertEqual(plan.total, Decimal("50000"))

    def test_15000_package_with_5_modules(self):
        plan = calculate_pricing(
            Decimal("15000"),
            5,
            is_free=False,
        )

        self.assertEqual(
            plan.certificate_price,
            Decimal("4500"),
        )
        self.assertEqual(
            sum(plan.module_prices),
            Decimal("10500"),
        )

        for price in plan.module_prices:
            self.assertGreaterEqual(price, Decimal("1000"))
            self.assertEqual(price % Decimal("500"), 0)

        self.assertEqual(plan.total, Decimal("15000"))

    def test_15000_package_with_10_modules(self):
        plan = calculate_pricing(
            Decimal("15000"),
            10,
            is_free=False,
        )

        self.assertEqual(
            plan.certificate_price,
            Decimal("4500"),
        )
        self.assertEqual(
            sorted(plan.module_prices),
            [Decimal("1000")] * 9 + [Decimal("1500")],
        )

    def test_free_course_certificate_is_fixed_15000(self):
        plan = calculate_pricing(
            Decimal("0"),
            6,
            is_free=True,
        )

        self.assertEqual(
            plan.certificate_price,
            FREE_CERTIFICATE_PRICE,
        )
        self.assertEqual(
            plan.module_prices,
            tuple(Decimal("0") for _ in range(6)),
        )

    def test_impossible_low_package_is_rejected(self):
        with self.assertRaises(PricingError):
            calculate_pricing(
                Decimal("5000"),
                10,
                is_free=False,
            )

    def test_component_price_rules(self):
        self.assertEqual(
            validate_component_price(8500),
            Decimal("8500"),
        )

        with self.assertRaises(PricingError):
            validate_component_price(500)

        with self.assertRaises(PricingError):
            validate_component_price(8700)


class ExternalMediaSecurityTests(SimpleTestCase):
    def test_youtube_watch_url_becomes_privacy_embed(self):
        url = youtube_embed_url(
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        )
        self.assertEqual(
            url,
            "https://www.youtube-nocookie.com/embed/"
            "dQw4w9WgXcQ?rel=0&modestbranding=1",
        )

    def test_youtu_be_link_is_supported(self):
        self.assertEqual(
            youtube_video_id(
                "https://youtu.be/dQw4w9WgXcQ"
            ),
            "dQw4w9WgXcQ",
        )

    def test_non_youtube_video_is_rejected(self):
        with self.assertRaises(ValidationError):
            youtube_embed_url(
                "https://example.com/video.mp4"
            )

    def test_soundcloud_player_only_for_soundcloud(self):
        self.assertIn(
            "w.soundcloud.com/player/",
            soundcloud_embed_url(
                "https://soundcloud.com/example/lesson"
            ),
        )
        self.assertEqual(
            soundcloud_embed_url(
                "https://example.com/audio"
            ),
            "",
        )


@override_settings(AUTO_COURSE_PRICING_ENABLED=True)
class FullPackageCertificateTests(TestCase):
    def test_completed_full_course_payment_includes_certificate(self):
        user = User.objects.create_user(
            username="package-student",
            email="package@example.com",
            password="pass",
        )

        course = Course.objects.create(
            title="Full Package Course",
            is_free=False,
            price=Decimal("50000"),
        )

        CoursePayment.objects.create(
            user=user,
            course=course,
            amount=Decimal("50000"),
            status="completed",
        )

        self.assertTrue(
            full_course_payment_includes_certificate(
                user,
                course,
            )
        )
