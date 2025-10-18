# ars_network/urls.py

from django.urls import path
from . import views

urlpatterns = [
    # Rotas de Teste/Validação
    # A rota raiz do app pode ser uma página inicial simples
    path('', views.home_page, name='home'),
    
    # Rotas de Autenticação (Ainda que não usemos a coleta por API, é bom tê-las)
    path('login/', views.spotify_login, name='spotify-login'),
    path('callback/', views.spotify_callback, name='spotify-callback'),
    path('user-info/', views.user_info, name='user-info'), 
    
    # Rota Principal para a Importação dos Dados CSV do MGD+
    # Você a executará via linha de comando, mas esta view serve como um fallback.
    path('import/mgd-data/', views.import_mgd_data_view, name='import-mgd-data'),
]