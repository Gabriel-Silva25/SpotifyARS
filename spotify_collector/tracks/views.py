# tracks/views.py
from django.shortcuts import redirect, HttpResponse
import spotipy
from spotipy.oauth2 import SpotifyOAuth, SpotifyClientCredentials
from django.conf import settings
from .models import Track
from .utils import get_spotify_audio_features, get_track_popularity  # mantive caso use em outro lugar
from spotipy.exceptions import SpotifyException, SpotifyOauthError
import re
import json
from typing import List, Iterable

SPOTIFY_SCOPES = "playlist-read-private playlist-read-collaborative user-library-read user-read-email user-top-read"

def get_spotify_oauth():
    """Retorna um objeto SpotifyOAuth com as configurações."""
    return SpotifyOAuth(
        client_id=settings.SPOTIFY_CLIENT_ID,
        client_secret=settings.SPOTIFY_CLIENT_SECRET,
        redirect_uri=settings.SPOTIFY_REDIRECT_URI,
        scope=SPOTIFY_SCOPES,
        cache_path=None,
        show_dialog=True,
    )

def _get_sp_client(request):
    """Obtém ou renova o token e retorna um cliente Spotipy ou None."""
    token_info = request.session.get("token_info")
    if not token_info:
        return None

    oauth = get_spotify_oauth()
    try:
        if oauth.is_token_expired(token_info):
            token_info = oauth.refresh_access_token(token_info["refresh_token"])
            request.session["token_info"] = token_info
            request.session.modified = True
    except (SpotifyOauthError, Exception) as e:
        print(f"Erro ao renovar o token: {e}")
        return None

    return spotipy.Spotify(auth=token_info["access_token"])

def spotify_login(request):
    """Redireciona o usuário para a página de autorização do Spotify."""
    oauth = get_spotify_oauth()
    auth_url = oauth.get_authorize_url()
    return redirect(auth_url)

def spotify_callback(request):
    """
    Captura o callback do Spotify, obtém o token de acesso
    e o salva na sessão do usuário.
    """
    oauth = get_spotify_oauth()
    code = request.GET.get('code')
    error = request.GET.get('error')

    if error:
        return HttpResponse(f"Erro na autorização: {error}", status=403)
    
    if not code:
        return HttpResponse("Código de autorização não encontrado.", status=400)

    try:
        token_info = oauth.get_access_token(code, check_cache=False)
        request.session['token_info'] = token_info
        request.session.modified = True
        # Redireciona para uma página de sucesso, como 'meus-dados'
        return redirect('meus-dados') 
    except (SpotifyOauthError, Exception) as e:
        return HttpResponse(f"Erro ao obter o token: {e}", status=500)

def meus_dados(request):
    """
    Uma view de exemplo para testar se a autenticação funcionou,
    exibindo os dados do usuário.
    """
    sp = _get_sp_client(request)
    if not sp:
        return redirect('spotify-login') # Usa o nome da rota

    try:
        user_info = sp.me()
        # Em um app real, você renderizaria um template aqui
        return HttpResponse(f"<h1>Olá, {user_info['display_name']}!</h1><p>Seu email é {user_info['email']}.</p><p>Login bem-sucedido. Agora você pode usar as outras rotas.</p>")
    except SpotifyException as e:
        return HttpResponse(f"Erro ao buscar dados do Spotify: {e}", status=500)

# utilidade: extrai o id mesmo se receber URL ou URI do Spotify
def _extract_spotify_id(s: str) -> str:
    if not s:
        return None
    s = s.strip()
    # abrange formatos como:
    # https://open.spotify.com/track/{id}
    # spotify:track:{id}
    m = re.search(r'(?:open\.spotify\.com/(?:track|playlist|album)/|spotify:(?:track:|playlist:|album:))([A-Za-z0-9]+)', s)
    if m:
        return m.group(1)
    # se já for só o id
    return s

def _chunks(iterable: Iterable, n: int):
    """Yield successive n-sized chunks from iterable."""
    it = list(iterable)
    for i in range(0, len(it), n):
        yield it[i:i + n]

def import_track(request, track_id):
    """
    Importa uma única música pelo track_id (ou URL/URI).
    Exemplo de rota: /import/track/<track_id>/
    """
    sp = _get_sp_client(request)
    if not sp:
        return redirect("/login/")

    tid = _extract_spotify_id(track_id)
    if not tid:
        return HttpResponse("track_id inválido", status=400)

    try:
        track = sp.track(tid)
        if not track or not track.get("id"):
            return HttpResponse("Música não encontrada.", status=404)

        audio_features_list = sp.audio_features([tid])
        audio = audio_features_list[0] if audio_features_list else {}

        artist = (track.get("artists") or [{}])[0].get("name", "-")
        album = (track.get("album") or {}).get("name", "-")
        popularity = track.get("popularity", 0)

        Track.objects.get_or_create(
            spotify_id=tid,
            defaults={
                "name": track.get("name"),
                "artist": artist,
                "album": album,
                "popularity": popularity,
                "tempo": audio.get("tempo"),
                "valence": audio.get("valence"),
                "speechiness": audio.get("speechiness"),
                "danceability": audio.get("danceability"),
                "liveness": audio.get("liveness"),
                "velocity": 0,
                "mean_popularity": popularity,
                "median_popularity": popularity,
                "std_popularity": 0,
                "retrieval_frequency": 1,
                "trend": "stable",
            },
        )
        return HttpResponse(f"Música {tid} importada com sucesso!")
    except SpotifyException as e:
        status = getattr(e, "http_status", 500)
        msg = getattr(e, "msg", str(e))
        return HttpResponse(f"Acesso negado pela API do Spotify ({status}). Motivo: {msg}", status=status)
    except Exception as e:
        return HttpResponse(f"Ocorreu um erro inesperado: {str(e)}", status=500)


def import_tracks(request):
    """
    Importa múltiplas músicas.
    Aceita:
    - GET  ?track_ids=id1,id2,id3
    - POST JSON {"track_ids": ["id1","id2"]} ou {"track_ids": "id1,id2"}
    IDs podem ser apenas o id ou URLs/URIs do Spotify.
    """
    sp = _get_sp_client(request)
    if not sp:
        return redirect("/login/")

    # obter track_ids de GET ou POST
    track_ids = None
    if request.method == "GET":
        track_ids = request.GET.get("track_ids")
    else:
        # tenta JSON primeiro
        try:
            body = request.body.decode()
            if body:
                data = json.loads(body)
                track_ids = data.get("track_ids")
        except Exception:
            # fallback para form-encoded
            track_ids = request.POST.get("track_ids") or track_ids

    if not track_ids:
        return HttpResponse("Parâmetro 'track_ids' não informado.", status=400)

    # normaliza para lista
    if isinstance(track_ids, str):
        # aceita tanto CSV quanto JSON string single id
        track_ids = [t.strip() for t in track_ids.split(",") if t.strip()]

    # extrai ids válidos e remove duplicatas
    cleaned_ids = []
    for t in track_ids:
        tid = _extract_spotify_id(t)
        if tid:
            cleaned_ids.append(tid)
    cleaned_ids = list(dict.fromkeys(cleaned_ids))  # dedupe mantendo ordem

    if not cleaned_ids:
        return HttpResponse("Nenhum track_id válido encontrado.", status=400)

    imported = []
    skipped = []
    try:
        # Spotify limita a 50 itens para sp.tracks; audio_features aceita 100.
        for batch in _chunks(cleaned_ids, 50):
            tracks_response = sp.tracks(batch).get("tracks", [])
            ids_in_batch = [t.get("id") for t in tracks_response if t and t.get("id")]
            # buscar audio features do batch (até 100)
            audio_features = sp.audio_features(ids_in_batch) or []
            af_map = {af.get("id"): af for af in audio_features if af and af.get("id")}

            for tr in tracks_response:
                if not tr or not tr.get("id"):
                    skipped.append(tr)
                    continue
                tid = tr.get("id")
                name = tr.get("name")
                artist = (tr.get("artists") or [{}])[0].get("name", "-")
                album = (tr.get("album") or {}).get("name", "-")
                popularity = tr.get("popularity", 0)
                audio = af_map.get(tid, {})

                Track.objects.get_or_create(
                    spotify_id=tid,
                    defaults={
                        "name": name,
                        "artist": artist,
                        "album": album,
                        "popularity": popularity,
                        "tempo": audio.get("tempo"),
                        "valence": audio.get("valence"),
                        "speechiness": audio.get("speechiness"),
                        "danceability": audio.get("danceability"),
                        "liveness": audio.get("liveness"),
                        "velocity": 0,
                        "mean_popularity": popularity,
                        "median_popularity": popularity,
                        "std_popularity": 0,
                        "retrieval_frequency": 1,
                        "trend": "stable",
                    },
                )
                imported.append(tid)

        return HttpResponse(f"Importadas: {len(imported)} faixas. IDs: {', '.join(imported)}")
    except SpotifyException as e:
        status = getattr(e, "http_status", 500)
        msg = getattr(e, "msg", str(e))
        return HttpResponse(f"Acesso negado pela API do Spotify ({status}). Motivo: {msg}", status=status)
    except Exception as e:
        return HttpResponse(f"Ocorreu um erro inesperado: {str(e)}", status=500)

# tracks/views.py (adicione ao final)
# tracks/views.py

# ... (imports e outras views) ...

# tracks/views.py

# ... (imports e outras views) ...

def bulk_import_by_name(request):
    try:
        auth_manager = SpotifyClientCredentials(
            client_id=settings.SPOTIFY_CLIENT_ID,
            client_secret=settings.SPOTIFY_CLIENT_SECRET
        )
        sp = spotipy.Spotify(auth_manager=auth_manager)
    except Exception as e:
        return HttpResponse(f"Erro na autenticação do aplicativo: {e}", status=500)

    music_list = [
    'All The Stars (with SZA) - Kendrick Lamar', # Removido o "From Black Panther..."
    'Pirata e Tesouro - Ferrugem'                 # Removido o "Ao vivo"
    ]

    imported, not_found = [], []
    tracks_to_process = []  # Lista para guardar os dados temporários

    print("\n--- ETAPA 1: BUSCANDO TODAS AS MÚSICAS ---")
    for entry in music_list:
        try:
            if " - " in entry:
                title, artist = entry.split(" - ", 1)
                query = f"track:{title.strip()} artist:{artist.strip()}"
            else:
                query = f"track:{entry.strip()}"
            
            result = sp.search(q=query, type="track", limit=1)
            items = result.get("tracks", {}).get("items", [])
            
            if not items:
                not_found.append(f"{entry} (não encontrado na busca)")
                continue
            
            # Guarda os dados da música para processar depois
            tracks_to_process.append(items[0])

        except Exception as e:
            not_found.append(f"{entry} (erro na busca: {e})")

    print(f"--- ETAPA 2: BUSCANDO AUDIO FEATURES PARA {len(tracks_to_process)} MÚSICAS EM LOTE ---")
    if tracks_to_process:
        track_ids = [t['id'] for t in tracks_to_process]
        
        # A API tem um limite de 100 por chamada, então dividimos em lotes (chunks)
        audio_features_list = []
        for i in range(0, len(track_ids), 100):
            chunk = track_ids[i:i + 100]
            try:
                features = sp.audio_features(chunk)
                audio_features_list.extend(features)
            except Exception as e:
                 print(f"Erro ao buscar audio_features para o lote {i}: {e}")

        # Cria um mapa para facilitar a busca: { 'track_id': {features} }
        audio_features_map = {f['id']: f for f in audio_features_list if f}

        print("--- ETAPA 3: SALVANDO TUDO NO BANCO DE DADOS ---")
        for track_data in tracks_to_process:
            try:
                tid = track_data["id"]
                artist_obj = track_data["artists"][0]
                
                # Buscamos os gêneros individualmente
                artist_info = sp.artist(artist_obj["id"])
                genres = artist_info.get("genres", [])
                
                # Pegamos os audio features do nosso mapa
                audio = audio_features_map.get(tid, {})

                Track.objects.update_or_create(
                    spotify_id=tid,
                    defaults={
                        "name": track_data["name"], "artist": artist_obj["name"],
                        "album": track_data.get("album", {}).get("name", "-"),
                        "popularity": track_data.get("popularity", 0),
                        "tempo": audio.get("tempo"), "valence": audio.get("valence"),
                        "speechiness": audio.get("speechiness"), "danceability": audio.get("danceability"),
                        "liveness": audio.get("liveness"), "velocity": 0,
                        "mean_popularity": track_data.get("popularity", 0),
                        "median_popularity": track_data.get("popularity", 0),
                        "std_popularity": 0, "retrieval_frequency": 1,
                        "trend": "stable", "genres": ", ".join(genres)  
                    },
                )
                imported.append(f"{track_data['name']} ({artist_obj['name']})")
            
            except Exception as e:
                not_found.append(f"{track_data['name']} (erro ao salvar: {e})")

    return HttpResponse(
        f"<h1>Importação Concluída!</h1>"
        f"<b>Importadas:</b> {len(imported)} músicas.<br>"
        f"<b>Não encontradas:</b> {len(not_found)}<br><br>"
        f"<b>Não encontradas (detalhes):</b><pre>{not_found}</pre>"
    )

# NOVA FUNÇÃO DE TESTE PARA DIAGNÓSTICO
def debug_spotify(request):
    """
    Uma view de teste para fazer UMA ÚNICA chamada à API do Spotify
    e ver exatamente qual é o erro.
    """
    print("--- INICIANDO TESTE DE DEBUG SPOTIFY ---")
    
    try:
        # Passo 1: Carregar as credenciais
        client_id = settings.SPOTIFY_CLIENT_ID
        client_secret = settings.SPOTIFY_CLIENT_SECRET
        
        # Passo 2: Imprimir as credenciais para garantir que estão sendo carregadas corretamente
        print(f"ID do Cliente Carregado na View: {client_id}")
        print(f"Segredo do Cliente Carregado na View: {'*' * len(client_secret) if client_secret else None}")

        if not client_id or not client_secret:
            return HttpResponse("Erro: Credenciais não encontradas nas configurações do Django.")

        # Passo 3: Tentar autenticar
        print("Tentando autenticar com SpotifyClientCredentials...")
        auth_manager = SpotifyClientCredentials(client_id=client_id, client_secret=client_secret)
        sp = spotipy.Spotify(auth_manager=auth_manager)
        print("Autenticação bem-sucedida.")

        # Passo 4: Fazer a busca mais simples possível
        print("Tentando fazer uma busca simples por 'love'...")
        results = sp.search(q='love', type='track', limit=1)
        print("Busca realizada com sucesso!")
        
        # Se chegarmos aqui, tudo funcionou
        primeira_musica = results['tracks']['items'][0]['name']
        return HttpResponse(f"<h1>Teste bem-sucedido!</h1><p>A API respondeu. Primeira música encontrada: {primeira_musica}</p>")

    except Exception as e:
        # Se algo der errado, imprimir o erro completo no terminal
        print("\n!!! OCORREU UM ERRO DURANTE O TESTE !!!")
        print(f"Tipo de Exceção: {type(e)}")
        print(f"Detalhes da Exceção: {e}")
        print("--- FIM DO TESTE DE DEBUG ---")
        
        # E mostrar uma mensagem de erro no navegador
        return HttpResponse(f"<h1>O teste falhou.</h1><p>Verifique o terminal do `runserver` para ver o erro detalhado.</p>", status=500)
