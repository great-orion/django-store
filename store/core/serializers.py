from rest_framework import serializers
from . import models


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Category
        fields = '__all__'


class ProductListSerializer(serializers.ModelSerializer):
    category = CategorySerializer()
    class Meta:
        model = models.Product
        fields = '__all__'


class AddToCartSerializer(serializers.Serializer):
    product_id = serializers.IntegerField()


class CartSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    count = serializers.IntegerField()

