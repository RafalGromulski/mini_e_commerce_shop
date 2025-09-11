"""API views (DRF) for categories, products, orders, and sales statistics."""

from typing import Type

from django.db.models import QuerySet, Sum
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework import mixins, parsers, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .filters import ProductFilter
from .models import Category, Product, Order, OrderItem
from .permissions import IsSellerOrReadOnly, IsSeller, is_seller
from .serializers import (
    CategorySerializer,
    ProductSerializer,
    OrderCreateSerializer,
    OrderDetailSerializer,
    TopProductsQuerySerializer,
    TopProductStatsSerializer
)


@extend_schema(tags=["Categories"])
class CategoryViewSet(viewsets.ModelViewSet):
    """
    CRUD for product categories.

    Read access is public.
    Create/update/delete is limited to "seller" users (we treat staff users as sellers).
    """
    queryset = Category.objects.all().order_by("name")
    serializer_class = CategorySerializer
    permission_classes = [IsSellerOrReadOnly]
    pagination_class = None  # categories are typically few; disable pagination


@extend_schema(tags=["Products"])
class ProductViewSet(viewsets.ModelViewSet):
    """
    List/retrieve/CRUD for products with filtering, ordering, and pagination.

    Public read access; write operations require a seller (staff) account.
    """
    queryset = Product.objects.select_related("category").all().order_by("name")
    serializer_class = ProductSerializer
    permission_classes = [IsSellerOrReadOnly]

    # Support JSON, form-data, and multipart (for image uploads via Swagger/cURL)
    parser_classes = [parsers.JSONParser, parsers.FormParser, parsers.MultiPartParser]

    # Filtering & ordering (as required by the task)
    filterset_class = ProductFilter
    ordering_fields = ["name", "price", "category__name"]  # name, category, price
    ordering = ["name"]  # default ordering


@extend_schema(tags=["Orders"])
class OrderViewSet(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet
):
    """
    Create an order (POST /api/orders/) and list/retrieve orders.

    - Authenticated customers see only their own orders.
    - Sellers (staff) can see all orders.
    """
    queryset = (
        Order.objects.select_related("customer")
        .prefetch_related("items__product")
        .all()
    )
    permission_classes = [IsAuthenticated]
    parser_classes = [parsers.JSONParser]

    def get_queryset(self) -> QuerySet[Order]:
        qs = super().get_queryset()
        return qs if is_seller(self.request.user) else qs.filter(customer=self.request.user)

    def get_serializer_class(self) -> Type[OrderCreateSerializer | OrderDetailSerializer]:
        # Use a dedicated serializer on create (input: shipping_address + items),
        # and a read-only detail serializer for list/retrieve.
        return OrderCreateSerializer if self.action == "create" else OrderDetailSerializer


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
    responses={200: TopProductStatsSerializer(many=True)},
)
class TopProductsStatsView(APIView):
    """
    Top-N most frequently ordered products within a date range (inclusive).

    GET /api/stats/top-products/?date_from=YYYY-MM-DD&date_to=YYYY-MM-DD&limit=N
    Access: sellers only (is_staff).
    """
    permission_classes = [IsSeller]

    @staticmethod
    def get(request, *args, **kwargs):
        # Validate and parse query params
        params = TopProductsQuerySerializer(data=request.query_params)
        params.is_valid(raise_exception=True)
        date_from = params.validated_data["date_from"]
        date_to = params.validated_data["date_to"]
        limit = params.validated_data["limit"]

        # Aggregate total units by product across the date range (inclusive)
        rows = (
            OrderItem.objects
            .filter(order__created_at__date__range=(date_from, date_to))
            .values("product", "product__name")
            .annotate(units_ordered=Sum("quantity"))
            .order_by("-units_ordered", "product")[:limit]
        )

        data = [
            {
                "product_id": r["product"],
                "product_name": r["product__name"],
                "units_ordered": int(r["units_ordered"] or 0),
            }
            for r in rows
        ]
        return Response(TopProductStatsSerializer(data, many=True).data)
