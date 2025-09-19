"""API views (DRF) for categories, products, orders, and sales statistics."""

from typing import Any, Type, cast

from django.db.models import Sum
from django.db.models.functions import TruncDate
from django_filters import FilterSet
from django_stubs_ext import QuerySetAny as DJQuerySet
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import mixins, parsers, viewsets
from rest_framework.pagination import BasePagination
from rest_framework.parsers import BaseParser
from rest_framework.permissions import BasePermission, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.serializers import BaseSerializer
from rest_framework.views import APIView

from .filters import ProductFilter
from .models import Category, Order, OrderItem, Product
from .permissions import IsSeller, IsSellerOrReadOnly, is_seller
from .serializers import (
    CategorySerializer,
    OrderCreateSerializer,
    OrderDetailSerializer,
    ProductSerializer,
    TopProductsQuerySerializer,
    TopProductStatsSerializer,
)


@extend_schema(tags=["Categories"])
class CategoryViewSet(viewsets.ModelViewSet):
    """
    CRUD for product categories.

    Read access is public.
    Create/update/delete is limited to "seller" users (we treat staff users as sellers).
    """

    queryset = Category.objects.all().order_by("name")
    serializer_class: type[BaseSerializer] = CategorySerializer
    permission_classes: list[type[BasePermission]] = [IsSellerOrReadOnly]
    pagination_class: type[BasePagination] | None = (
        None  # categories are typically few; disable pagination
    )


@extend_schema(tags=["Products"])
class ProductViewSet(viewsets.ModelViewSet):
    """
    List/retrieve/CRUD for products with filtering, ordering, and pagination.

    Public read access; write operations require a seller (staff) account.
    """

    queryset = Product.objects.select_related("category").all().order_by("name")
    serializer_class: type[BaseSerializer] = ProductSerializer
    permission_classes: list[type[BasePermission]] = [IsSellerOrReadOnly]

    # Support JSON, form-data, and multipart (for image uploads via Swagger/cURL)
    parser_classes: list[type[BaseParser]] = [
        parsers.JSONParser,
        parsers.FormParser,
        parsers.MultiPartParser,
    ]

    # Filtering & ordering (as required by the task)
    filterset_class: type[FilterSet] = ProductFilter
    ordering_fields: list[str] = ["name", "price", "category__name"]  # name, category, price
    ordering: list[str] = ["name"]  # default ordering


@extend_schema(tags=["Orders"])
class OrderViewSet(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    """
    Create an order (POST /api/orders/) and list/retrieve orders.

    - Authenticated customers see only their own orders.
    - Sellers (staff) can see all orders.
    """

    queryset = Order.objects.select_related("customer").prefetch_related("items__product").all()
    permission_classes: list[type[BasePermission]] = [IsAuthenticated]
    parser_classes: list[type[BaseParser]] = [parsers.JSONParser]

    def get_queryset(self) -> DJQuerySet[Order, Order]:
        qs = cast(DJQuerySet[Order, Order], super().get_queryset())
        user = self.request.user
        if is_seller(user):
            return qs
        # IsAuthenticated guarantees authenticated at runtime; assert narrows for mypy
        assert user.is_authenticated
        return qs.filter(customer_id=user.id)

    def get_serializer_class(self) -> Type[OrderCreateSerializer | OrderDetailSerializer]:
        # Use a dedicated serializer on create (input: shipping_address + items),
        # and a read-only detail serializer for list/retrieve.
        return OrderCreateSerializer if self.action == "create" else OrderDetailSerializer


_TOP_PRODUCTS_RESPONSES: dict[int, Any] = cast(
    dict[int, Any], {200: TopProductStatsSerializer(many=True)}
)


@extend_schema(
    tags=["Stats"],
    parameters=[
        OpenApiParameter(
            name="date_from",
            type=OpenApiTypes.DATE,
            location="query",
            required=True,
            description="Start date (YYYY-MM-DD)",
        ),
        OpenApiParameter(
            name="date_to",
            type=OpenApiTypes.DATE,
            location="query",
            required=True,
            description="End date (YYYY-MM-DD)",
        ),
        OpenApiParameter(
            name="limit",
            type=OpenApiTypes.INT,
            location="query",
            required=False,
            description="Max number of products (default 10)",
        ),
    ],
    responses=_TOP_PRODUCTS_RESPONSES,
)
class TopProductsStatsView(APIView):
    """
    Top-N most frequently ordered products within a date range (inclusive).

    GET /api/stats/top-products/?date_from=YYYY-MM-DD&date_to=YYYY-MM-DD&limit=N
    Access: sellers only (is_staff).
    """

    permission_classes: list[type[BasePermission]] = [IsSeller]

    def get(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        # Validate and parse query params
        params = TopProductsQuerySerializer(data=request.query_params)
        params.is_valid(raise_exception=True)
        date_from = params.validated_data["date_from"]
        date_to = params.validated_data["date_to"]
        limit = params.validated_data["limit"]

        # Aggregate total units by product across the date range (inclusive)
        rows = list(
            OrderItem.objects.annotate(created_date=TruncDate("order__created_at"))
            .filter(created_date__range=(date_from, date_to))
            .values("product", "product__name")
            .annotate(units_ordered=Sum("quantity"))
            .order_by("-units_ordered", "product")[:limit]
        )

        # Normalize to a strictly-typed payload for the serializer
        data: list[dict[str, Any]] = [
            {
                "product_id": int(r["product"]),
                "product_name": str(r["product__name"]),
                "units_ordered": int(r["units_ordered"] or 0),
            }
            for r in rows
        ]

        serializer = TopProductStatsSerializer(data, many=True)  # instance, nie data=
        return Response(serializer.data)
