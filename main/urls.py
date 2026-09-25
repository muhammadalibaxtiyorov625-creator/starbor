from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('send-contact/', views.send_contact, name='send_contact'),
    path('telegram-webhook/', views.telegram_webhook, name='telegram_webhook'),
    path('javob-olish/<int:buyurtma_id>/', views.javob_olish, name='javob_olish'),
    path('googleec6e8bba19eb9bcf.html', views.google_verification, name='google_verification'),
]
