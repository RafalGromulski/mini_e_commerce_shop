"""Celery tasks for the Shop app."""

import logging
import smtplib
from datetime import timedelta

from celery import shared_task
from django.core.mail import send_mail
from django.utils import timezone

from .models import Order

logger = logging.getLogger(__name__)


@shared_task
def send_payment_reminders() -> int:
    """
    Send email reminders for orders whose payment is due *tomorrow*.

    Rules:
    - Skip orders already marked as paid or already reminded.
    - Count only successfully sent emails in the return value.
    - Mark `payment_reminder_sent=True` after a successful send.
      (Note: without a separate “claimed” flag, two workers could race and
       send duplicates. In typical setups a single beat + single worker runs
       this task, so it's acceptable. If you need strict idempotency across
       workers, introduce a separate claim/lock field.)

    Returns:
        int: number of successfully sent reminders.
    """
    tomorrow = timezone.localdate() + timedelta(days=1)

    qs = (
        Order.objects
        .select_related("customer")
        .filter(
            payment_due_date=tomorrow,
            is_paid=False,
            payment_reminder_sent=False,
        )
        .order_by("pk")
    )

    sent = 0
    for order in qs.iterator(chunk_size=500):
        email = order.customer.email
        if not email:
            continue

        lines = [
            f"Hi {order.customer.get_full_name() or order.customer.username},",
            f"This is a reminder to pay for order #{order.pk}.",
            f"Total: {order.total_price} PLN",
            f"Payment due date: {order.payment_due_date}",
            "",
            "If you have already paid, you can ignore this message.",
        ]
        try:
            # send_mail returns the number of successfully delivered messages (1 or 0)
            delivered = send_mail(
                subject=f"Payment reminder for order #{order.pk}",
                message="\n".join(lines),
                from_email=None,  # uses DEFAULT_FROM_EMAIL
                recipient_list=[email],
                fail_silently=False,
            )
        except (smtplib.SMTPException, OSError) as exc:
            logger.warning(
                "Failed to send payment reminder for Order(id=%s) to %s: %s",
                order.pk, email, exc
            )
            continue

        if delivered:
            order.payment_reminder_sent = True
            order.save(update_fields=["payment_reminder_sent"])
            sent += 1
        else:
            logger.warning(
                "send_mail returned 0 for Order(id=%s) to %s (no recipients or backend issue).",
                order.pk, email
            )

    logger.info("Payment reminders sent: %s", sent)
    return sent
