from django.urls import path

from . import views

urlpatterns = [
    path('10m', views.index10m, name='index10m'),
    path('', views.index, name='index'),
]
