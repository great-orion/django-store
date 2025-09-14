from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from .models import Product

class StaticViewSitemap(Sitemap):
    priority = 0.8
    changefreq = 'weekly'

    def items(self):
        # Return names of your URL patterns for static pages
        return ['core:product_list', 'core:cart_show', 'core:verify']

    def location(self, item):
        return reverse(item)

class ProductSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.9

    def items(self):
        # Only include products that are enabled, not deleted, and in stock
        return Product.objects.filter(
            enabled=True,
            deleted=False,
            count__gt=0
        )

    def lastmod(self, obj):
        return obj.modified_date

    def location(self, obj):
        return reverse('core:product_list')