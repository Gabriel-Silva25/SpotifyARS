import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import os
from dotenv import load_dotenv

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()

# Pega as credenciais do ambiente
client_id = os.getenv("SPOTIFY_CLIENT_ID")
client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")

# Verifica se as credenciais foram carregadas
if not client_id or not client_secret:
    print("Erro: As credenciais SPOTIFY_CLIENT_ID e SPOTIFY_CLIENT_SECRET não foram encontradas.")
    print("Certifique-se de que seu arquivo .env está na mesma pasta e configurado corretamente.")
else:
    # Autentica usando o método Client Credentials
    auth_manager = SpotifyClientCredentials(client_id=client_id, client_secret=client_secret)
    sp = spotipy.Spotify(auth_manager=auth_manager)

    # COLE O ID DA PLAYLIST PÚBLICA QUE VOCÊ QUER ANALISAR AQUI
    playlist_id = '3xkTWI9l7pxb03n2Vu7QbC'  # Exemplo: Playlist "Today's Top Hits"
    # --------------------------------------------------------------------

    try:
        results = sp.playlist_items(playlist_id)
        tracks = results['items']

        # Lida com a paginação para playlists com mais de 100 músicas
        while results['next']:
            results = sp.next(results)
            tracks.extend(results['items'])

        # --- MUDANÇA #1: Criar uma lista para armazenar os resultados ---
        music_list_for_code = []

        for item in tracks:
            track = item.get('track')
            # Garante que o item é uma música válida e não um arquivo local ou episódio
            if track and track.get('name') and track.get('artists'):
                track_name = track['name']
                artist_name = track['artists'][0]['name']
                
                # Formata a string no padrão "Música - Artista"
                formatted_string = f"{track_name} - {artist_name}"
                
                # Adiciona a string formatada à nossa lista
                music_list_for_code.append(formatted_string)

        # --- MUDANÇA #2: Imprimir a lista final no formato de código Python ---
        print("# Copie e cole este bloco de código na sua view 'bulk_import_by_name'")
        print("music_list = [")
        for entry in music_list_for_code:
            # Escapa as aspas duplas dentro do nome para não quebrar o código
            processed_entry = entry.replace('"', '\\"')
            print(f'    "{processed_entry}",')
        print("]")


    except spotipy.exceptions.SpotifyException as e:
        print(f"Ocorreu um erro ao buscar a playlist: {e}")
    except Exception as e:
        print(f"Um erro inesperado aconteceu: {e}")