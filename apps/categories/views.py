from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q
from .models import Category, CategoryAttribute, CategoryAttributeValue
from .serializers import (
    CategorySerializer, CategoryListSerializer, CategoryDetailSerializer,
    CategoryAttributeSerializer, CategoryAttributeValueSerializer,
    CategoryAttributeDetailSerializer, CategoryAttributeValueDetailSerializer
)


class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    lookup_field = 'slug'
    permission_classes = [permissions.IsAdminUser]
    
    def get_permissions(self):
        if self.action in ['list', 'retrieve', 'root_categories', 'by_parent']:
            return [permissions.AllowAny()]
        return super().get_permissions()
    
    def get_serializer_class(self):
        if self.action == 'list':
            return CategoryListSerializer
        elif self.action == 'retrieve':
            return CategoryDetailSerializer
        return CategorySerializer
    
    def get_queryset(self):
        queryset = Category.objects.all()
        if self.action in ['list', 'root_categories', 'by_parent']:
            queryset = queryset.filter(is_active=True)
        return queryset
    
    @action(detail=False, methods=['get'])
    def root_categories(self, request):
        categories = Category.objects.filter(parent=None, is_active=True)
        serializer = CategoryListSerializer(categories, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def by_parent(self, request):
        parent_slug = request.query_params.get('parent', None)
        if parent_slug:
            try:
                parent = Category.objects.get(slug=parent_slug)
                categories = Category.objects.filter(parent=parent, is_active=True)
                serializer = CategoryListSerializer(categories, many=True)
                return Response(serializer.data)
            except Category.DoesNotExist:
                return Response({'error': 'دسته‌بندی والد یافت نشد'}, status=status.HTTP_404_NOT_FOUND)
        else:
            return Response({'error': 'پارامتر parent الزامی است'}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['get'])
    def attributes(self, request, slug=None):
        category = self.get_object()
        # دریافت ویژگی‌های این دسته و تمام دسته‌های والد
        attributes = []
        current = category
        while current:
            attrs = CategoryAttribute.objects.filter(category=current)
            for attr in attrs:
                attributes.append(attr)
            current = current.parent
        
        serializer = CategoryAttributeDetailSerializer(attributes, many=True)
        return Response(serializer.data)


class CategoryAttributeViewSet(viewsets.ModelViewSet):
    queryset = CategoryAttribute.objects.all()
    serializer_class = CategoryAttributeSerializer
    permission_classes = [permissions.IsAdminUser]
    
    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [permissions.AllowAny()]
        return super().get_permissions()
    
    def get_serializer_class(self):
        if self.action in ['retrieve', 'list']:
            return CategoryAttributeDetailSerializer
        return CategoryAttributeSerializer


class CategoryAttributeValueViewSet(viewsets.ModelViewSet):
    queryset = CategoryAttributeValue.objects.all()
    serializer_class = CategoryAttributeValueSerializer
    permission_classes = [permissions.IsAdminUser]
    
    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [permissions.AllowAny()]
        return super().get_permissions()
    
    def get_serializer_class(self):
        if self.action in ['retrieve', 'list']:
            return CategoryAttributeValueDetailSerializer
        return CategoryAttributeValueSerializer