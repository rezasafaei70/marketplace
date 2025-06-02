from rest_framework import serializers
from django.db.models import Avg
from django.utils.text import slugify
import uuid

from .models import (
    Product, ProductImage, ProductAttribute, ProductVariant, ProductVariantAttribute,
    ProductTag, ProductTagRelation, ProductReview, ProductReviewImage, ProductReviewComment,
    ProductQuestion, ProductAnswer, RelatedProduct, ProductInventoryLog
)
from apps.categories.serializers import CategoryListSerializer, CategoryAttributeSerializer
from apps.sellers.serializers import SellerListSerializer


class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ('id', 'image', 'alt_text', 'is_primary', 'order')


class ProductAttributeSerializer(serializers.ModelSerializer):
    attribute_name = serializers.SerializerMethodField()
    
    class Meta:
        model = ProductAttribute
        fields = ('id', 'attribute', 'attribute_name', 'value')
    
    def get_attribute_name(self, obj):
        return obj.attribute.name


class ProductVariantAttributeSerializer(serializers.ModelSerializer):
    attribute_name = serializers.SerializerMethodField()
    
    class Meta:
        model = ProductVariantAttribute
        fields = ('id', 'attribute', 'attribute_name', 'value')
    
    def get_attribute_name(self, obj):
        return obj.attribute.name


class ProductVariantSerializer(serializers.ModelSerializer):
    attributes = ProductVariantAttributeSerializer(many=True, read_only=True)
    final_price = serializers.DecimalField(max_digits=15, decimal_places=0, read_only=True)
    
    class Meta:
        model = ProductVariant
        fields = ('id', 'name', 'sku', 'price_adjustment', 'stock', 'image', 
                 'is_default', 'attributes', 'final_price')


class ProductTagSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductTag
        fields = ('id', 'name', 'slug')


class ProductReviewImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductReviewImage
        fields = ('id', 'image')


class ProductReviewCommentSerializer(serializers.ModelSerializer):
    user_full_name = serializers.SerializerMethodField()
    
    class Meta:
        model = ProductReviewComment
        fields = ('id', 'comment', 'user_full_name', 'is_seller', 'created_at')
        read_only_fields = ('is_seller', 'created_at')
    
    def get_user_full_name(self, obj):
        return obj.user.get_full_name()


class ProductReviewSerializer(serializers.ModelSerializer):
    user_full_name = serializers.SerializerMethodField()
    images = ProductReviewImageSerializer(many=True, read_only=True)
    comments = ProductReviewCommentSerializer(many=True, read_only=True)
    uploaded_images = serializers.ListField(
        child=serializers.ImageField(max_length=1000000, allow_empty_file=False, use_url=False),
        write_only=True, required=False
    )
    
    class Meta:
        model = ProductReview
        fields = ('id', 'rating', 'title', 'comment', 'user_full_name', 
                 'created_at', 'images', 'comments', 'uploaded_images')
        read_only_fields = ('user_full_name', 'created_at')
    
    def get_user_full_name(self, obj):
        return obj.user.get_full_name()
    
    def create(self, validated_data):
        uploaded_images = validated_data.pop('uploaded_images', [])
        review = ProductReview.objects.create(**validated_data)
        
        for image in uploaded_images:
            ProductReviewImage.objects.create(review=review, image=image)
        
        return review


class ProductAnswerSerializer(serializers.ModelSerializer):
    user_full_name = serializers.SerializerMethodField()
    
    class Meta:
        model = ProductAnswer
        fields = ('id', 'answer', 'user_full_name', 'is_seller', 'created_at')
        read_only_fields = ('is_seller', 'created_at')
    
    def get_user_full_name(self, obj):
        return obj.user.get_full_name()


class ProductQuestionSerializer(serializers.ModelSerializer):
    user_full_name = serializers.SerializerMethodField()
    answers = ProductAnswerSerializer(many=True, read_only=True)
    
    class Meta:
        model = ProductQuestion
        fields = ('id', 'question', 'user_full_name', 'created_at', 'answers')
        read_only_fields = ('user_full_name', 'created_at')
    
    def get_user_full_name(self, obj):
        return obj.user.get_full_name()


class ProductListSerializer(serializers.ModelSerializer):
    primary_image = serializers.SerializerMethodField()
    discount_percentage = serializers.IntegerField(read_only=True)
    final_price = serializers.DecimalField(max_digits=15, decimal_places=0, read_only=True)
    seller_name = serializers.SerializerMethodField()
    category_name = serializers.SerializerMethodField()
    
    class Meta:
        model = Product
        fields = ('id', 'name', 'slug', 'short_description', 'price', 'discount_price',
                 'discount_percentage', 'final_price', 'rating', 'review_count',
                 'primary_image', 'seller_name', 'category_name', 'is_in_stock')
    
    def get_primary_image(self, obj):
        primary_image = obj.images.filter(is_primary=True).first()
        if primary_image:
            return primary_image.image.url
        # اگر تصویر اصلی وجود نداشت، اولین تصویر را برمی‌گرداند
        first_image = obj.images.first()
        if first_image:
            return first_image.image.url
        return None
    
    def get_seller_name(self, obj):
        return obj.seller.shop_name
    
    def get_category_name(self, obj):
        return obj.category.name


class RelatedProductSerializer(serializers.ModelSerializer):
    related_product = ProductListSerializer(read_only=True)
    
    class Meta:
        model = RelatedProduct
        fields = ('id', 'related_product')


class ProductDetailSerializer(serializers.ModelSerializer):
    images = ProductImageSerializer(many=True, read_only=True)
    attributes = ProductAttributeSerializer(many=True, read_only=True)
    variants = ProductVariantSerializer(many=True, read_only=True)
    tags = serializers.SerializerMethodField()
    related_products = RelatedProductSerializer(many=True, read_only=True)
    reviews = ProductReviewSerializer(many=True, read_only=True)
    questions = ProductQuestionSerializer(many=True, read_only=True)
    seller = SellerListSerializer(read_only=True)
    category = CategoryListSerializer(read_only=True)
    discount_percentage = serializers.IntegerField(read_only=True)
    final_price = serializers.DecimalField(max_digits=15, decimal_places=0, read_only=True)
    
    class Meta:
        model = Product
        fields = ('id', 'name', 'slug', 'description', 'short_description', 'price',
                 'discount_price', 'discount_percentage', 'final_price', 'stock',
                 'is_active', 'is_featured', 'rating', 'review_count', 'sales_count',
                 'view_count', 'sku', 'weight', 'width', 'height', 'length',
                 'meta_title', 'meta_description', 'meta_keywords', 'created_at',
                 'updated_at', 'seller', 'category', 'images', 'attributes',
                 'variants', 'tags', 'related_products', 'reviews', 'questions',
                 'is_in_stock')
    
    def get_tags(self, obj):
        tags = ProductTag.objects.filter(products__product=obj)
        return ProductTagSerializer(tags, many=True).data


class ProductCreateUpdateSerializer(serializers.ModelSerializer):
    uploaded_images = serializers.ListField(
        child=serializers.ImageField(max_length=1000000, allow_empty_file=False, use_url=False),
        write_only=True, required=False
    )
    primary_image = serializers.ImageField(write_only=True, required=False)
    attributes = serializers.ListField(
        child=serializers.JSONField(),
        write_only=True, required=False
    )
    variants = serializers.ListField(
        child=serializers.JSONField(),
        write_only=True, required=False
    )
    tags = serializers.ListField(
        child=serializers.CharField(max_length=100),
        write_only=True, required=False
    )
    
    class Meta:
        model = Product
        fields = ('name', 'category', 'description', 'short_description', 'price',
                 'discount_price', 'stock', 'sku', 'weight', 'width', 'height', 'length',
                 'meta_title', 'meta_description', 'meta_keywords', 'uploaded_images',
                 'primary_image', 'attributes', 'variants', 'tags')
    
    def create(self, validated_data):
        uploaded_images = validated_data.pop('uploaded_images', [])
        primary_image = validated_data.pop('primary_image', None)
        attributes_data = validated_data.pop('attributes', [])
        variants_data = validated_data.pop('variants', [])
        tags_data = validated_data.pop('tags', [])
        
        # ایجاد محصول
        product = Product.objects.create(**validated_data)
        
        # ذخیره تصاویر
        if primary_image:
            ProductImage.objects.create(product=product, image=primary_image, is_primary=True, order=0)
        
        for i, image in enumerate(uploaded_images, start=1):
            ProductImage.objects.create(product=product, image=image, order=i)
        
        # ذخیره ویژگی‌ها
        for attr_data in attributes_data:
            ProductAttribute.objects.create(
                product=product,
                attribute_id=attr_data['attribute_id'],
                value=attr_data['value']
            )
        
        # ذخیره تنوع‌ها
        for variant_data in variants_data:
            variant = ProductVariant.objects.create(
                product=product,
                name=variant_data['name'],
                sku=variant_data.get('sku'),
                price_adjustment=variant_data.get('price_adjustment', 0),
                stock=variant_data.get('stock', 0),
                image=variant_data.get('image'),
                is_default=variant_data.get('is_default', False)
            )
            
            # ذخیره ویژگی‌های تنوع
            for attr in variant_data.get('attributes', []):
                ProductVariantAttribute.objects.create(
                    variant=variant,
                    attribute_id=attr['attribute_id'],
                    value=attr['value']
                )
        
        # ذخیره برچسب‌ها
        for tag_name in tags_data:
            tag, created = ProductTag.objects.get_or_create(
                name=tag_name,
                defaults={'slug': slugify(tag_name)}
            )
            ProductTagRelation.objects.create(product=product, tag=tag)
        
        return product
    
    def update(self, instance, validated_data):
        uploaded_images = validated_data.pop('uploaded_images', [])
        primary_image = validated_data.pop('primary_image', None)
        attributes_data = validated_data.pop('attributes', [])
        variants_data = validated_data.pop('variants', [])
        tags_data = validated_data.pop('tags', [])
        
        # به‌روزرسانی فیلدهای محصول
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # به‌روزرسانی تصاویر
        if primary_image:
            # حذف تصویر اصلی قبلی
            ProductImage.objects.filter(product=instance, is_primary=True).delete()
            ProductImage.objects.create(product=instance, image=primary_image, is_primary=True, order=0)
        
        for i, image in enumerate(uploaded_images, start=1):
            ProductImage.objects.create(product=instance, image=image, order=i)
        
        # به‌روزرسانی ویژگی‌ها
        if attributes_data:
            # حذف ویژگی‌های قبلی
            ProductAttribute.objects.filter(product=instance).delete()
            
            # ایجاد ویژگی‌های جدید
            for attr_data in attributes_data:
                ProductAttribute.objects.create(
                    product=instance,
                    attribute_id=attr_data['attribute_id'],
                    value=attr_data['value']
                )
        
        # به‌روزرسانی تنوع‌ها
        if variants_data:
            # حذف تنوع‌های قبلی
            ProductVariant.objects.filter(product=instance).delete()
            
            # ایجاد تنوع‌های جدید
            for variant_data in variants_data:
                variant = ProductVariant.objects.create(
                    product=instance,
                    name=variant_data['name'],
                    sku=variant_data.get('sku'),
                    price_adjustment=variant_data.get('price_adjustment', 0),
                    stock=variant_data.get('stock', 0),
                    image=variant_data.get('image'),
                    is_default=variant_data.get('is_default', False)
                )
                
                # ذخیره ویژگی‌های تنوع
                for attr in variant_data.get('attributes', []):
                    ProductVariantAttribute.objects.create(
                        variant=variant,
                        attribute_id=attr['attribute_id'],
                        value=attr['value']
                    )
        
        # به‌روزرسانی برچسب‌ها
        if tags_data:
            # حذف روابط برچسب قبلی
            ProductTagRelation.objects.filter(product=instance).delete()
            
            # ایجاد روابط برچسب جدید
            for tag_name in tags_data:
                tag, created = ProductTag.objects.get_or_create(
                    name=tag_name,
                    defaults={'slug': slugify(tag_name)}
                )
                ProductTagRelation.objects.create(product=instance, tag=tag)
        
        return instance


class ProductInventoryLogSerializer(serializers.ModelSerializer):
    product_name = serializers.SerializerMethodField()
    variant_name = serializers.SerializerMethodField()
    created_by_name = serializers.SerializerMethodField()
    
    class Meta:
        model = ProductInventoryLog
        fields = ('id', 'product', 'product_name', 'variant', 'variant_name',
                 'previous_stock', 'new_stock', 'change_reason', 'reference',
                 'created_by', 'created_by_name', 'created_at')
        read_only_fields = ('id', 'created_at')
    
    def get_product_name(self, obj):
        return obj.product.name
    
    def get_variant_name(self, obj):
        if obj.variant:
            return obj.variant.name
        return None
    
    def get_created_by_name(self, obj):
        if obj.created_by:
            return obj.created_by.get_full_name()
        return None