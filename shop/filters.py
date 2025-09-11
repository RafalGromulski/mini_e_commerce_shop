"""FilterSet for the Product list endpoint."""

from django_filters import rest_framework as filters

from .models import Category, Product


class ProductFilter(filters.FilterSet):
    """
    Supported query params on /api/products/:
    - name: case-insensitive substring match on product name
    - description: case-insensitive substring match
    - category: filter by category ID
    - category_name: case-insensitive substring match on category name
    - price: exact price match
    - min_price / max_price: inclusive price range
    """

    # Text filters (case-insensitive contains)
    name = filters.CharFilter(field_name="name", lookup_expr="icontains")
    description = filters.CharFilter(field_name="description", lookup_expr="icontains")

    # Category: by ID or by category name (handy in tests)
    category = filters.ModelChoiceFilter(queryset=Category.objects.all())
    category_name = filters.CharFilter(field_name="category__name", lookup_expr="icontains")

    # Price: exact or range
    price = filters.NumberFilter(field_name="price")
    min_price = filters.NumberFilter(field_name="price", lookup_expr="gte")
    max_price = filters.NumberFilter(field_name="price", lookup_expr="lte")

    class Meta:
        model = Product
        fields = [
            "name",
            "description",
            "category",
            "category_name",
            "price",
            "min_price",
            "max_price",
        ]
