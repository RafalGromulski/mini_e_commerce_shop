"""Celery tasks for the Shop app.

This module defines asynchronous tasks executed by Celery workers,
e.g. sending payment reminder emails to customers.
"""

from __future__ import annotations

import logging
import smtplib
from datetime import timedelta
from typing import Any, Final, Optional

from celery import Task, shared_task
from django.core.mail import send_mail
from django.utils import timezone

from .models import Order

logger = logging.getLogger(__name__)

# Batch size used when iterating through querysets in tasks
_CHUNK_SIZE: Final[int] = 500


class TaskRequestLike:
    """Minimal interface to describe Celery's Task.request object."""

    id: str
    retries: int
    hostname: str


class PaymentReminderTask(Task):
    """Custom Celery Task class used for payment reminder jobs.

    Extends the base Task class to improve type checking
    and explicitly declare commonly accessed attributes/methods.
    """

    def retry(
        self,
        *,
        exc: Optional[BaseException] = None,
        countdown: Optional[int] = None,
        max_retries: Optional[int] = None,
        **kwargs: Any,
    ) -> Any:
        """Retry this task with exponential backoff."""
        return super().retry(exc=exc, countdown=countdown, max_retries=max_retries, **kwargs)

    # Type hint for the request object (populated at runtime by Celery)
    request: TaskRequestLike


@shared_task(
    bind=True,
    base=PaymentReminderTask,
    autoretry_for=(smtplib.SMTPException, OSError),
    retry_backoff=True,
    retry_jitter=True,
    retry_kwargs={"max_retries": 5},
    rate_limit="20/m",
)
def send_payment_reminders(_self: PaymentReminderTask) -> int:
    """Send email reminders for orders whose payment is due tomorrow.

    Business rules:
      * Skip orders already paid or already reminded.
      * Count only successfully sent emails in the return value.
      * Mark ``payment_reminder_sent=True`` after a successful send.

    Notes:
      * Without a dedicated "claimed" field, two workers could race and send duplicates.
        In typical setups (single beat + single worker) this is acceptable.
        For strict idempotency across workers, introduce a claim/lock field on ``Order``.

    Returns:
        int: Number of successfully sent reminders.
    """
    tomorrow = timezone.localdate() + timedelta(days=1)

    # Select all unpaid, unreminded orders with due date = tomorrow
    qs = (
        Order.objects.select_related("customer")
        .filter(
            payment_due_date=tomorrow,
            is_paid=False,
            payment_reminder_sent=False,
        )
        .order_by("pk")
    )

    sent = 0
    # Iterate in chunks to avoid loading too many rows into memory
    for order in qs.iterator(chunk_size=_CHUNK_SIZE):
        email = getattr(order.customer, "email", None)
        if not email:
            logger.debug("Order %s: no email for customer -> skip", order.pk)
            continue

        greeting = (
            order.customer.get_full_name() or getattr(order.customer, "username", "") or "Customer"
        )
        body_lines = [
            f"Hi {greeting},",
            f"This is a reminder to pay for order #{order.pk}.",
            f"Total: {order.total_price} PLN",
            f"Payment due date: {order.payment_due_date}",
            "",
            "If you have already paid, you can ignore this message.",
        ]
        # send_mail returns 1 on success
        delivered = send_mail(
            subject=f"Payment reminder for order #{order.pk}",
            message="\n".join(body_lines),
            from_email=None,  # uses DEFAULT_FROM_EMAIL
            recipient_list=[email],
            fail_silently=False,
        )

        if delivered:
            # Mark reminder as sent
            order.payment_reminder_sent = True
            order.save(update_fields=["payment_reminder_sent"])
            sent += 1
            logger.info("Payment reminder sent | order=%s email=%s", order.pk, email)
        else:
            logger.warning("send_mail returned 0 | order=%s email=%s", order.pk, email)

    logger.info("Payment reminders summary | sent=%s", sent)
    return sent
