"""Django signals for post-save/delete hooks on OrderItem and Product.

- Recalculate order totals whenever an OrderItem is saved or deleted.
  NOTE: bulk_create() does not emit post_save signals. In our create-order flow
  we compute the total explicitly, so that's OK.

- Remove image files after a Product is deleted. Missing files are ignored,
  real file/path issues are logged (but do not crash the signal).
"""

import logging
from contextlib import suppress

from django.core.exceptions import SuspiciousFileOperation
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .models import OrderItem, Product

logger = logging.getLogger(__name__)


@receiver(
    post_save,
    sender=OrderItem,
    dispatch_uid="orderitem_recalculate_total_on_save",
)
def recalc_order_total_on_orderitem_save(sender, instance: OrderItem, **kwargs) -> None:
    """Recompute the parent order's total after saving an OrderItem."""
    instance.order.recalculate_totals()


@receiver(
    post_delete,
    sender=OrderItem,
    dispatch_uid="orderitem_recalculate_total_on_delete",
)
def recalc_order_total_on_orderitem_delete(sender, instance: OrderItem, **kwargs) -> None:
    """Recompute the parent order's total after deleting an OrderItem."""
    instance.order.recalculate_totals()


@receiver(
    post_delete,
    sender=Product,
    dispatch_uid="product_delete_cleanup_files",
)
def cleanup_product_files_after_delete(sender, instance: Product, **kwargs) -> None:
    """
    Delete product image files after the Product row is removed.

    - Silently ignore missing files (FileNotFoundError).
    - Log filesystem/path problems (OSError, SuspiciousFileOperation).
    """
    for field in ("image", "thumbnail"):
        f = getattr(instance, field, None)
        if not f or not getattr(f, "name", None) or not getattr(f, "storage", None):
            continue

        # FileSystemStorage.delete() already ignores missing files, but other
        # storages may raise FileNotFoundError – suppress that specific case.
        with suppress(FileNotFoundError):
            try:
                f.storage.delete(f.name)
            except (OSError, SuspiciousFileOperation) as e:
                logger.warning(
                    "Failed to delete file '%s' for Product(id=%s): %s",
                    f.name,
                    instance.pk,
                    e,
                )
