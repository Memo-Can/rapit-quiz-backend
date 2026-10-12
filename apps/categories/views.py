from drf_spectacular.utils import extend_schema
from rest_framework.generics import ListAPIView

from .models import Category
from .serializers import CategorySerializer


@extend_schema(summary="Kategori listesi")
class CategoryListView(ListAPIView):
    queryset = Category.objects.filter(is_active=True)
    serializer_class = CategorySerializer
    pagination_class = None
