import logging

from django.conf import settings
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .models import CertificateTemplate, Course, CourseModule
from .pricing import (
    PricingError,
    apply_course_pricing,
    effective_certificate_price,
)


logger = logging.getLogger(__name__)


def _enabled():
    return bool(
        getattr(settings, "AUTO_COURSE_PRICING_ENABLED", False)
    )


def _refresh(course):
    if not _enabled():
        return

    try:
        apply_course_pricing(course)
    except PricingError as exc:
        # Do not destroy legacy prices when the package is too small.
        # Module checkout independently refuses invalid automatic pricing.
        logger.warning(
            "Automatic pricing skipped for course %s: %s",
            course.pk,
            exc,
        )


@receiver(
    post_save,
    sender=Course,
    dispatch_uid="chuosmart_auto_price_course",
)
def auto_price_course(sender, instance, **kwargs):
    _refresh(instance)


@receiver(
    post_save,
    sender=CourseModule,
    dispatch_uid="chuosmart_auto_price_module_save",
)
def auto_price_module_save(sender, instance, **kwargs):
    _refresh(instance.course)


@receiver(
    post_delete,
    sender=CourseModule,
    dispatch_uid="chuosmart_auto_price_module_delete",
)
def auto_price_module_delete(sender, instance, **kwargs):
    course = Course.objects.filter(pk=instance.course_id).first()
    if course:
        _refresh(course)


@receiver(
    post_save,
    sender=CertificateTemplate,
    dispatch_uid="chuosmart_enforce_certificate_price",
)
def enforce_certificate_price(sender, instance, **kwargs):
    if not _enabled():
        return

    target = effective_certificate_price(
        instance.course,
        template=instance,
    )

    if instance.certificate_price != target:
        CertificateTemplate.objects.filter(pk=instance.pk).update(
            certificate_price=target
        )
