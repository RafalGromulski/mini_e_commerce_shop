"""Application URL routing for the Shop API: products, categories, orders, and stats."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    CategoryViewSet,
    OrderViewSet,
    ProductViewSet,
    TopProductsStatsView
)

# Router with standard DRF viewset routes
router = DefaultRouter()
router.register(r"products", ProductViewSet, basename="product")
router.register(r"categories", CategoryViewSet, basename="category")
router.register(r"orders", OrderViewSet, basename="order")

# Namespacing helps with reverse('shop:product-list') / reverse('shop:order-detail', args=[pk])
app_name = "shop"

urlpatterns = [
    path("", include(router.urls)),
    path("stats/top-products/", TopProductsStatsView.as_view(), name="stats-top-products"),
]
