# ars_network/views.py

from django.shortcuts import HttpResponse

# --- Views de Placeholder ---

def home_page(request):
    return HttpResponse("<h1>Projeto ARS Spotify (Mercado BR)</h1><p>Estrutura de URLs OK. Por favor, rode as migrações e o comando de importação de dados.</p>")

def spotify_login(request):
    return HttpResponse("Login Placeholder")

def spotify_callback(request):
    return HttpResponse("Callback Placeholder")

def user_info(request):
    return HttpResponse("User Info Placeholder")

def import_mgd_data_view(request):
    # Esta rota apenas instrui o usuário a rodar o comando customizado
    return HttpResponse("Para importar os dados, você deve rodar o comando customizado do Django no terminal (não via navegador): python manage.py import_mgd_data")