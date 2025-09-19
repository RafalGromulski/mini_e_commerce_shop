"""DRF serializers for categories, products, orders, and stats."""

import logging
from decimal import Decimal
from typing import Any, List, Optional

from django.core.mail import send_mail
from django.db import DatabaseError, transaction
from django.utils import timezone
from rest_framework import serializers

from .models import Category, Order, OrderItem, Product

logger = logging.getLogger(__name__)


# ----------------------------- Category & Product -----------------------------
class CategorySerializer(serializers.ModelSerializer):
    """Simple representation of a product category."""

    class Meta:
        model = Category
        fields = ["id", "name"]


class ProductSerializer(serializers.ModelSerializer):
    """
    Product serializer.

    - `category`: write with PK, expose `category_name` read-only.
    - `thumbnail`: read-only, generated automatically.
    """

    category = serializers.PrimaryKeyRelatedField(queryset=Category.objects.all())
    category_name = serializers.CharField(source="category.name", read_only=True)
    image = serializers.ImageField(required=False, allow_null=True)
    thumbnail = serializers.ImageField(read_only=True)

    class Meta:
        model = Product
        fields = [
            "id",
            "name",
            "description",
            "price",
            "category",
            "category_name",
            "image",
            "thumbnail",
            "created_at",
        ]
        read_only_fields = ["id", "thumbnail", "created_at", "category_name"]

    @staticmethod
    def validate_price(value: Optional[Decimal]) -> Decimal:
        """Ensure price is non-negative (model has a validator too)."""
        if value is None or value < 0:
            raise serializers.ValidationError("Price must be non-negative.")
        return value


# --------------------------------- Orders ------------------------------------


class OrderItemCreateSerializer(serializers.Serializer):
    """Input for a single order line when creating an order."""

    product = serializers.PrimaryKeyRelatedField(queryset=Product.objects.all())
    quantity = serializers.IntegerField(min_value=1)


class OrderDetailItemSerializer(serializers.ModelSerializer):
    """Read-only representation of a single order line."""

    product_name = serializers.CharField(source="product.name", read_only=True)

    class Meta:
        model = OrderItem
        fields = ["product", "product_name", "quantity", "unit_price"]


class OrderDetailSerializer(serializers.ModelSerializer):
    """Read-only representation of an order with its items."""

    items = OrderDetailItemSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = [
            "id",
            "customer",
            "shipping_address",
            "created_at",
            "payment_due_date",
            "total_price",
            "items",
        ]
        read_only_fields = fields


class OrderCreateSerializer(serializers.Serializer):
    """
    Input/Output contract for order creation.

    Input:
    - full_name (optional): saved to the user profile as best effort
    - shipping_address: required
    - items: list of {"product": <id>, "quantity": <int >= 1>}

    Output:
    - id, total_price, payment_due_date, created_at
    """

    # input
    full_name = serializers.CharField(write_only=True, required=False, allow_blank=True)
    shipping_address = serializers.CharField()
    items = OrderItemCreateSerializer(many=True, write_only=True)

    # output
    id = serializers.IntegerField(read_only=True)
    total_price = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    payment_due_date = serializers.DateField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)

    @staticmethod
    def validate_items(items: List[dict]) -> List[dict]:
        """Require a non-empty items list."""
        if not items:
            raise serializers.ValidationError("Items list must not be empty.")
        return items

    def create(self, validated_data: dict[str, Any]) -> Order:
        """
        Create order + lines, compute totals, set due date (+5 days) and send a confirmation email.
        """
        user = self.context["request"].user
        full_name = validated_data.pop("full_name", "").strip()
        items_in = validated_data.pop("items")

        with transaction.atomic():
            order = Order.objects.create(customer=user, **validated_data)

            # Build line items and compute total
            total = Decimal("0.00")
            order_items: List[OrderItem] = []
            for item in items_in:
                product = item["product"]
                qty = int(item["quantity"])
                unit_price = product.price
                order_items.append(
                    OrderItem(order=order, product=product, quantity=qty, unit_price=unit_price)
                )
                total += unit_price * qty

            OrderItem.objects.bulk_create(order_items)
            order.total_price = total

            # Ensure payment due date is set (+5 days from today)
            if not order.payment_due_date:
                from datetime import timedelta

                order.payment_due_date = timezone.localdate() + timedelta(days=5)

            order.save(update_fields=["total_price", "payment_due_date"])

        # Best-effort: update user's name if provided
        if full_name:
            first, _, last = full_name.partition(" ")
            first = first.strip()
            last = last.strip()

            # Truncate to field max lengths to avoid DataError
            first_len = getattr(user._meta.get_field("first_name"), "max_length", None)
            last_len = getattr(user._meta.get_field("last_name"), "max_length", None)
            if first_len:
                first = first[:first_len]
            if last_len:
                last = last[:last_len]

            try:
                # Direct UPDATE avoids model signals and is cheaper than save()
                type(user).objects.filter(pk=user.pk).update(first_name=first, last_name=last)
            except DatabaseError as e:
                # Don't fail order creation because of a profile update hiccup
                logger.warning("Failed to update user's name (id=%s): %s", user.pk, e)

        self._send_confirmation_email(user, order)
        return order

    @staticmethod
    def _send_confirmation_email(user: Any, order: Order) -> None:
        """Send a plain-text confirmation email (console backend in dev)."""
        lines = [
            f"Hi {user.get_full_name() or user.username},",
            f"Thank you for your order #{order.pk}.",
            f"Total: {order.total_price} PLN",
            f"Payment due date: {order.payment_due_date}",
            "",
            "Items:",
        ]
        for it in order.items.select_related("product"):
            lines.append(f"- {it.product.name} × {it.quantity} = {it.unit_price * it.quantity} PLN")
        send_mail(
            subject=f"Order confirmation #{order.pk}",
            message="\n".join(lines),
            from_email=None,  # uses DEFAULT_FROM_EMAIL; with console backend it prints to stdout
            recipient_list=[user.email] if user.email else [],
            fail_silently=True,
        )


# ---------------------------------- Stats ------------------------------------


class TopProductsQuerySerializer(serializers.Serializer):
    """Query parameters for the 'top products' stats endpoint."""

    date_from = serializers.DateField()
    date_to = serializers.DateField()
    limit = serializers.IntegerField(min_value=1, max_value=100, default=10)

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        if attrs["date_from"] > attrs["date_to"]:
            raise serializers.ValidationError("date_from must not be after date_to.")
        return attrs


class TopProductStatsSerializer(serializers.Serializer):
    """Single row in the 'top products' result."""

    product_id = serializers.IntegerField()
    product_name = serializers.CharField()
    units_ordered = serializers.IntegerField()
