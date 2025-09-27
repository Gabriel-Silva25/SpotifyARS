"""
URL configuration for spotify_collector project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
# spotify_collector/urls.py
from django.contrib import admin
from django.urls import path
from tracks import views

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Rotas de autenticação (agora funcionais)
    path('login/', views.spotify_login, name='spotify-login'),
    path('callback/', views.spotify_callback, name='spotify-callback'),
    path('meus-dados/', views.meus_dados, name='meus-dados'),

    # Rotas para as suas views de importação (que antes estavam inacessíveis)
    # Ex: /import/track/4iV5W9uYEdYUVa79Axb7Rh/
    path('import/track/<str:track_id>/', views.import_track, name='import-track'),
    
    # Ex: /import/tracks/?track_ids=id1,id2
    path('import/tracks/', views.import_tracks, name='import-tracks'),
    
    # Ex: /import/by-name/
    path('import/by-name/', views.bulk_import_by_name, name='import-by-name'),
     # ADICIONE ESTA LINHA PARA O NOSSO TESTE
    path('debug/', views.debug_spotify, name='debug-spotify'),
]