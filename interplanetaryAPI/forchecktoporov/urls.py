from django.urls import path
from . import views

urlpatterns = [
    path('company/<str:company_name>/', views.company, name='company'),
    path('common-friends/<str:people_uuids>/', views.commonfriends, name='common-friends'),
    path('favourite-foods/<str:person_uuid>/', views.favourite_foods, name='favorite-foods'),
]