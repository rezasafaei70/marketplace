from rest_framework import serializers
from .models import Category, CategoryAttribute, CategoryAttributeValue


class CategoryAttributeValueSerializer(serializers.ModelSerializer):
    class Meta:
        model = CategoryAttributeValue
        fields = ('id', 'value', 'color_code', 'order')


class CategoryAttributeSerializer(serializers.ModelSerializer):
    values = CategoryAttributeValueSerializer(many=True, read_only=True)
    
    class Meta:
        model = CategoryAttribute
        fields = ('id', 'name', 'slug', 'is_required', 'is_filter', 'is_color', 'is_size', 'order', 'values')


class CategorySerializer(serializers.ModelSerializer):
    children = serializers.SerializerMethodField()
    attributes = CategoryAttributeSerializer(many=True, read_only=True)
    parent_name = serializers.SerializerMethodField()
    
    class Meta:
        model = Category
        fields = ('id', 'name', 'slug', 'description', 'parent', 'parent_name', 'image', 
                 'is_active', 'created_at', 'updated_at', 'order', 'children', 'attributes')
    
    def get_children(self, obj):
        return CategorySerializer(obj.get_children(), many=True).data
    
    def get_parent_name(self, obj):
        if obj.parent:
            return obj.parent.name
        return None


class CategoryListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ('id', 'name', 'slug', 'image', 'parent')


class CategoryDetailSerializer(serializers.ModelSerializer):
    children = CategoryListSerializer(many=True, read_only=True)
    attributes = CategoryAttributeSerializer(many=True, read_only=True)
    breadcrumbs = serializers.SerializerMethodField()
    
    class Meta:
        model = Category
        fields = ('id', 'name', 'slug', 'description', 'parent', 'image', 
                 'is_active', 'created_at', 'updated_at', 'order', 
                 'children', 'attributes', 'breadcrumbs')
    
    def get_breadcrumbs(self, obj):
        result = []
        node = obj
        while node:
            result.insert(0, {'id': node.id, 'name': node.name, 'slug': node.slug})
            node = node.parent
        return result


class CategoryAttributeValueDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = CategoryAttributeValue
        fields = '__all__'


class CategoryAttributeDetailSerializer(serializers.ModelSerializer):
    values = CategoryAttributeValueDetailSerializer(many=True, read_only=True)
    category_name = serializers.SerializerMethodField()
    
    class Meta:
        model = CategoryAttribute
        fields = '__all__'
    
    def get_category_name(self, obj):
        return obj.category.name