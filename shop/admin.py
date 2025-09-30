"""Django admin configuration for categories, products, and orders."""

from django.contrib import admin
from django.db.models import QuerySet
from django.http import HttpRequest
from django.utils.html import format_html

from .models import Category, Order, OrderItem, Product


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    """Admin for product categories."""

    search_fields = ["name"]
    list_display = ["name"]
    ordering = ["name"]


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    """Admin for products with small thumbnail preview."""

    list_display = ["name", "category", "price", "thumb_preview"]
    list_filter = ["category"]
    search_fields = ["name", "description", "category__name"]
    readonly_fields = ["thumbnail_preview"]
    autocomplete_fields = ["category"]
    list_select_related = ["category"]
    list_per_page = 50

    def get_queryset(self, request: HttpRequest) -> QuerySet[Product]:
        # Avoid N+1 on category in the changelist
        qs = super().get_queryset(request)
        return qs.select_related("category")

    @admin.display(description="Thumbnail")
    def thumb_preview(self, obj: Product) -> str:
        """Small thumbnail in list view."""
        if obj.thumbnail:
            return format_html('<img src="{url}" alt="thumb" height="40">', url=obj.thumbnail.url)
        return "—"

    @admin.display(description="Thumbnail preview")
    def thumbnail_preview(self, obj: Product) -> str:
        """Larger thumbnail in the detail view (readonly)."""
        if obj.thumbnail:
            return format_html('<img src="{url}" alt="thumb" height="150">', url=obj.thumbnail.url)
        return "—"


class OrderItemInline(admin.TabularInline):
    """Inline editor for order line items."""

    model = OrderItem
    extra = 0
    autocomplete_fields = ["product"]
    # Keep unit_price editable so admins can correct data if needed.


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    """Admin for orders with inline items and quick actions."""

    list_display = [
        "id",
        "customer",
        "created_at",
        "payment_due_date",
        "total_price",
        "is_paid",
        "payment_reminder_sent",
    ]
    list_filter = ["is_paid", "payment_reminder_sent"]
    search_fields = ["customer__username", "customer__email", "shipping_address"]
    date_hierarchy = "created_at"
    inlines = [OrderItemInline]
    actions = ["mark_paid", "mark_unpaid"]
    list_select_related = ["customer"]
    list_per_page = 50

    def get_queryset(self, request: HttpRequest) -> QuerySet[Order]:
        # Avoid N+1 on customer in the changelist
        qs = super().get_queryset(request)
        return qs.select_related("customer")

    @admin.action(description="Mark as paid")
    def mark_paid(self, request: HttpRequest, queryset: QuerySet[Order]) -> None:
        queryset.update(is_paid=True)

    @admin.action(description="Mark as unpaid")
    def mark_unpaid(self, request: HttpRequest, queryset: QuerySet[Order]) -> None:
        queryset.update(is_paid=False)
