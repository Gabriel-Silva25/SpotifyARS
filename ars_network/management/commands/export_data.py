# ars_network/management/commands/export_data.py

from django.core.management.base import BaseCommand
from ars_network.models import HitSong
import pandas as pd
from pathlib import Path
from django.conf import settings

class Command(BaseCommand):
    help = 'Exporta os dados de HitSongs, incluindo métricas ARS e colaboração, para um arquivo CSV/Excel.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("--- INICIANDO EXPORTAÇÃO DE DADOS PARA INSPEÇÃO ---"))
        
        # 1. Obter todos os dados do modelo HitSong com os artistas relacionados
        hit_songs = HitSong.objects.prefetch_related('artists').all()
        
        # 2. Criar uma lista para armazenar os dados tabulares
        data_list = []
        
        for song in hit_songs:
            # 2a. Extrair dados dos artistas
            artist_names = [a.name for a in song.artists.all()]
            artist_genres = [a.genres for a in song.artists.all()]

            # 2b. Formatar o resultado
            data_list.append({
                'song_id': song.spotify_id,
                'song_name': song.name,
                'popularity': song.popularity,
                
                # O CAMPO CRUCIAL DE INSPEÇÃO:
                'is_collaboration': song.is_collaboration,
                
                # Informações dos artistas
                'artist_names': "; ".join(artist_names), # Usa ponto e vírgula para separar artistas
                'artist_count': len(artist_names),
                'all_genres_list': artist_genres,
                
                # As variáveis preditivas e de controle calculadas
                'avg_artist_betweenness': song.avg_artist_betweenness,
                'genre_heterogeneity_index': song.genre_heterogeneity_index,
                'danceability': song.danceability,
                'energy': song.energy,
                'valence': song.valence,
            })

        # 3. Converter para DataFrame
        df = pd.DataFrame(data_list)
        
        # 4. Definir o caminho de saída
        BASE_DIR = settings.BASE_DIR
        output_dir = BASE_DIR / "data" / "analysis_output"
        output_dir.mkdir(exist_ok=True)
        
        output_path = output_dir / "ars_spotify_data_completa.csv"
        
        # 5. Salvar o arquivo (usando ; como delimitador para evitar conflito com nomes)
        df.to_csv(output_path, sep=';', index=False, encoding='utf-8-sig')

        self.stdout.write(self.style.SUCCESS(f"\n--- EXPORTAÇÃO CONCLUÍDA ---"))
        self.stdout.write(f"Arquivo salvo em: {output_path}")
        self.stdout.write(self.style.NOTICE("Aberto no Excel, use 'Dados -> De Texto/CSV' e use ; como delimitador."))