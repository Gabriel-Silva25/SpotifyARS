import os
import django
import csv

# Linhas mágicas para permitir que este script acesse o projeto Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'spotify_collector.settings')
django.setup()

# Importe seu modelo APÓS o setup do Django
from tracks.models import Track

def export_data():
    """
    Busca todas as músicas no banco de dados e as salva em um arquivo CSV.
    """
    print("Iniciando a exportação de dados...")

    # Nome do arquivo de saída
    filename = "musicas_exportadas.csv"

    # Cabeçalhos da planilha (você pode adicionar ou remover campos do seu modelo aqui)
    headers = [
        'name', 'artist', 'album', 'popularity', 'genres',
        'tempo', 'danceability', 'valence', 'liveness', 'speechiness'
    ]

    # Busca todos os objetos Track no banco de dados
    tracks = Track.objects.all()

    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        # Usamos DictWriter para facilitar, ele usa os nomes dos cabeçalhos
        writer = csv.DictWriter(csvfile, fieldnames=headers)

        # Escreve a primeira linha com os cabeçalhos
        writer.writeheader()

        # Itera sobre cada música e escreve uma linha no arquivo
        for track in tracks:
            writer.writerow({
                'name': track.name,
                'artist': track.artist,
                'album': track.album,
                'popularity': track.popularity,
                'genres': track.genres,
                'tempo': track.tempo,
                'danceability': track.danceability,
                'valence': track.valence,
                'liveness': track.liveness,
                'speechiness': track.speechiness,
            })

    print(f"Sucesso! {tracks.count()} músicas foram exportadas para o arquivo '{filename}'")

if __name__ == '__main__':
    export_data()