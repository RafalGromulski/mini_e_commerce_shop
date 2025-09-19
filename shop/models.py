"""
Domain models for the E-commerce API.

Includes:
- Category: simple product category (unique name).
- Product: product with automatic thumbnail generation (max width 200px).
- Order / OrderItem: order with line items, total recomputation helper, and
  a default payment due date set to +5 days.
"""

from datetime import timedelta
from decimal import Decimal
from io import BytesIO
from pathlib import Path
from typing import Any

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone
from PIL import Image, UnidentifiedImageError
from PIL.Image import Image as PILImage


def product_image_upload(instance: "Product", filename: str) -> str:
    """
    Compute a storage path for product images.

    New (unsaved) instances use a temporary folder; saved instances use their PK.
    Result: products/<pk or tmp>/<original_name>
    """
    base = "tmp" if not instance.pk else str(instance.pk)
    return f"products/{base}/{filename}"


def product_thumb_name(original_name: str, ext: str = "jpg") -> str:
    """
    Build a thumbnail filename from the original image name, forcing a .jpg extension
    (we save thumbnails as JPEG regardless of source format).

    Example: "coffee.png" -> "coffee_thumb.jpg"
    """
    p = Path(original_name)
    return f"{p.stem}_thumb.{ext}"


class Category(models.Model):
    """Product category."""

    name = models.CharField(max_length=120, unique=True)

    class Meta:
        ordering = ["name"]
        indexes = [models.Index(fields=["name"])]
        verbose_name = "Category"
        verbose_name_plural = "Categories"

    def __str__(self) -> str:
        return self.name


class Product(models.Model):
    """Product with pricing and images (original + auto-generated thumbnail)."""

    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name="products",
        verbose_name="Category",
    )
    name = models.CharField("Name", max_length=200)
    description = models.TextField("Description", blank=True)
    price = models.DecimalField(
        "Price",
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    image = models.ImageField("Image", upload_to=product_image_upload, blank=True, null=True)
    thumbnail = models.ImageField(
        "Thumbnail", upload_to=product_image_upload, blank=True, null=True, editable=False
    )
    created_at = models.DateTimeField(auto_now_add=True)

    # Thumbnail generation config
    THUMB_MAX_WIDTH = 200
    THUMB_QUALITY = 85  # JPEG quality 1..95

    class Meta:
        ordering = ["name"]
        indexes = [
            models.Index(fields=["name"]),
            models.Index(fields=["price"]),
        ]
        verbose_name = "Product"
        verbose_name_plural = "Products"

    def __str__(self) -> str:
        return self.name

    def save(self, *args: Any, **kwargs: Any) -> None:
        """
        Save the product and (re)generate a thumbnail when the main image changes.

        We first persist the model to obtain a PK (so upload paths can include it),
        then create/refresh the thumbnail if needed, and finally persist the thumbnail path.
        """
        image_changed = False

        if self.pk:
            old = Product.objects.filter(pk=self.pk).only("image", "thumbnail").first()
            if old and old.image != self.image:
                image_changed = True
        else:
            # New object — if an image is provided, generate a thumbnail after initial save.
            image_changed = bool(self.image)

        super().save(*args, **kwargs)

        # Generate/update thumbnail if needed
        if self.image and (image_changed or not self.thumbnail):
            if self._generate_thumbnail():
                super().save(update_fields=["thumbnail"])

    def _generate_thumbnail(self) -> bool:
        """
        Create a thumbnail with max width THUMB_MAX_WIDTH (no upscaling).

        Returns:
            True if the thumbnail was generated and assigned, False otherwise.
        """
        if not self.image:
            self.thumbnail = None
            return False

        try:
            # Load source image
            self.image.open("rb")
            pil_img: PILImage = Image.open(self.image)
            pil_img.load()

            # Normalize color mode (e.g., PNG with alpha) to RGB for JPEG
            if pil_img.mode not in ("RGB", "L"):
                pil_img = pil_img.convert("RGB")

            # Resize if wider than the target width
            w, h = pil_img.size
            if w > self.THUMB_MAX_WIDTH:
                new_w = self.THUMB_MAX_WIDTH
                new_h = int(h * (new_w / w))
                pil_img = pil_img.resize((new_w, new_h), Image.Resampling.LANCZOS)

            # Save to memory as JPEG
            out = BytesIO()
            pil_img.save(out, format="JPEG", quality=self.THUMB_QUALITY)
            out.seek(0)

            # Put thumbnail next to the original file
            folder = str(Path(self.image.name).parent)
            thumb_name = product_thumb_name(Path(self.image.name).name, ext="jpg")
            full_thumb_path = f"{folder}/{thumb_name}"

            self.thumbnail.save(full_thumb_path, ContentFile(out.read()), save=False)
            return True
        except (UnidentifiedImageError, OSError, ValueError):
            # Invalid image, IO error, or corrupted file – do not block product save.
            return False


class Order(models.Model):
    """Customer order with auto-calculated payment due date and total price."""

    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="orders",
        verbose_name="Customer",
    )
    shipping_address = models.CharField("Shipping address", max_length=255)
    created_at = models.DateTimeField("Created at", auto_now_add=True)
    payment_due_date = models.DateField("Payment due date", blank=True, null=True)
    total_price = models.DecimalField(
        "Total price",
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    is_paid = models.BooleanField("Paid", default=False)
    payment_reminder_sent = models.BooleanField("Reminder sent", default=False)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["created_at"])]
        verbose_name = "Order"
        verbose_name_plural = "Orders"

    def __str__(self) -> str:
        return f"Order #{self.pk} — {self.customer}"

    def save(self, *args: Any, **kwargs: Any) -> None:
        """
        Ensure payment_due_date is set on first save: created_at (or today) + 5 days.
        """
        if not self.payment_due_date:
            base = self.created_at.date() if self.pk else timezone.localdate()
            self.payment_due_date = base + timedelta(days=5)
        super().save(*args, **kwargs)

    def recalculate_totals(self) -> None:
        """
        Recompute and persist the order's total price from its items.
        """
        total = Decimal("0.00")
        for item in self.items.all():
            total += item.quantity * item.unit_price
        self.total_price = total
        super().save(update_fields=["total_price"])


class OrderItem(models.Model):
    """Single order line: product snapshot with its unit price at the moment of ordering."""

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="order_items")
    quantity = models.PositiveIntegerField("Quantity", default=1)
    unit_price = models.DecimalField(
        "Unit price",
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
        # No default: we snapshot from Product on first save if missing.
    )

    class Meta:
        verbose_name = "Order item"
        verbose_name_plural = "Order items"
        constraints = [
            models.UniqueConstraint(
                fields=["order", "product"],
                name="uq_orderitem_order_product",
            )
        ]

    def __str__(self) -> str:
        return f"{self.product} × {self.quantity}"

    def save(self, *args: Any, **kwargs: Any) -> None:
        """
        Snapshot the product price into unit_price on creation if not provided.
        """
        if self._state.adding and getattr(self, "unit_price", None) is None:
            self.unit_price = self.product.price
        super().save(*args, **kwargs)
