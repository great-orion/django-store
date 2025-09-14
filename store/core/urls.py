from django.urls import path
from . import views
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from django.contrib.sitemaps.views import sitemap
from core.sitemaps import StaticViewSitemap, ProductSitemap

# Define sitemap dictionary
sitemaps = {
    'static': StaticViewSitemap,
    'products': ProductSitemap,
}

app_name = 'core'


urlpatterns = [
    path('', views.ListProducts.as_view(), name='product_list'),
    path('cart/add/<int:item_id>', views.AddToCartView.as_view(), name='cart_add'),
    # path('cart/add/', views.AddToCartAPIView.as_view(), name='cart_add_api'),

    path('cart/remove/<int:item_id>', views.RemoveFromCartView.as_view(), name='cart_remove'),
    path('cart/empty', views.EmptyCartView.as_view(), name='cart_empty'),
    path('cart', views.ShowCartView.as_view(), name='cart_show'),
    path('checkout', views.CheckoutCartView.as_view(), name='checkout'),
    path('verify', views.VerifyView.as_view(), name='verify'),
    path('api/product', views.ProductListAPIView.as_view(), name='api_product'),
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('sitemap.xml', sitemap, {'sitemaps': sitemaps}, name='django.contrib.sitemaps.views.sitemap'),
    path('search/', views.SearchView.as_view(), name='search'),

]

