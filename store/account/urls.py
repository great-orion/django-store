
from django.urls import path, include
from . import views

app_name = 'account'

urlpatterns = [
    path('signup', views.SignupView.as_view(), name='signup'),
    path('activate/<str:uidb64>/<str:token>/', views.ActivateAccountView.as_view(), name='activate'),
]
