"""
URL configuration for projeto_spotify project.
# ... (comentários)
"""
from django.contrib import admin
from django.urls import path, include 


urlpatterns = [
    path("admin/", admin.site.urls),
    # Rota para as views de login e coleta no ars_network
    # A rota raiz ('') delega todas as URLs não capturadas para o app ars_network
    path('', include('ars_network.urls')), 
]