# ars_network/management/commands/import_mgd_data.py

import pandas as pd
from django.core.management.base import BaseCommand
from django.db import transaction
from pathlib import Path
from ars_network.models import Artist, HitSong
from django.conf import settings # <--- ESSENCIAL
from datetime import datetime

# 1. Obter o BASE_DIR a partir das configurações do Django (seguro)
BASE_DIR = settings.BASE_DIR 
PROCESSED_DIR = BASE_DIR / "data" / "processed" 

class Command(BaseCommand):
    help = 'Importa dados de Artistas e Hit Songs (filtrados para BR) do MGD+ para o banco de dados.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("--- INICIANDO IMPORTAÇÃO DO MGD+ (MERCADO BR) ---"))
        
        # 1. Carregar dados Parquet
        try:
            df_artists = pd.read_parquet(PROCESSED_DIR / "artists_br.parquet")
            df_hits = pd.read_parquet(PROCESSED_DIR / "hitsongs_br.parquet")
        except FileNotFoundError:
            self.stdout.write(self.style.ERROR(f"Arquivos Parquet não encontrados na pasta: {PROCESSED_DIR}"))
            self.stdout.write(self.style.NOTICE("Rode o script de pré-processamento novamente."))
            return
        
        # Limpa dados existentes para evitar duplicatas e conflitos na chave primária
        Artist.objects.all().delete()
        HitSong.objects.all().delete()

        # ----------------------------------------------------
        # 2. Importar Artistas (Nós da Rede)
        # ----------------------------------------------------
        self.stdout.write(self.style.SUCCESS(f"Importando {len(df_artists)} Artistas..."))
        artists_to_create = []
        for index, row in df_artists.iterrows():
            # Mapeamento do DataFrame para o Modelo Artist
            artists_to_create.append(
                Artist(
                    spotify_id=row['artist_id'],
                    name=row['name'],
                    # Salva a lista de gêneros como string (MGD+ original)
                    genres=row['genres'].strip('[]').replace("'", "").replace('"', ""),
                    artist_popularity=row['popularity'] if pd.notna(row['popularity']) else None,
                )
            )
        # Inserção em massa (Mais rápido)
        Artist.objects.bulk_create(artists_to_create, ignore_conflicts=True)
        self.stdout.write(self.style.SUCCESS("Artistas importados com sucesso."))

        # ----------------------------------------------------
        # 3. Importar Hit Songs (Fatos e Atributos)
        # ----------------------------------------------------
        self.stdout.write(self.style.SUCCESS(f"Importando {len(df_hits)} Hit Songs..."))
        
        # Mapeia IDs para objetos Artist para a ligação M:M posterior
        artist_obj_map = {a.spotify_id: a for a in Artist.objects.all()}

        with transaction.atomic():
            for index, row in df_hits.iterrows():
                
                # PREPARAÇÃO DE DADOS ANTES DA CRIAÇÃO
                try:
                    # Tenta converter a data, pode ser em formato diferente
                    release_date = pd.to_datetime(row['release_date'], errors='coerce').date()
                except:
                    release_date = None
                    
                is_collaboration = row.get('num_artists', 1) > 1 # Usa 1 como default se faltar
                
                # CORREÇÃO: Tratar valores NaN (Not a Number/Missing) no nome antes de criar
                song_name = row['song_name']
                if pd.isna(song_name) or not str(song_name).strip():
                    song_name = "Nome Desconhecido (ID: " + row['song_id'] + ")" 

                # FIM DA PREPARAÇÃO
                
                # CRIAÇÃO DO OBJETO HITSONG
                hit_song = HitSong.objects.create(
                    spotify_id=row['song_id'],
                    name=song_name, # USAR O VALOR TRATADO
                    
                    # Campos fixos e mapeados
                    album=row.get('album', "N/A"), # Usando 'album' como nome de coluna mais provável
                    popularity=row['popularity'] if pd.notna(row['popularity']) else 0,
                    release_date=release_date,
                    explicit=row['explicit'] if pd.notna(row['explicit']) else False,
                    is_collaboration=is_collaboration,
                    market_of_origin='BR - Brasil', # Fixo para o escopo
                    
                    # Atributos de Áudio (Todos são Flutuantes - FloatField)
                    danceability=row['danceability'] if pd.notna(row['danceability']) else None, 
                    energy=row['energy'] if pd.notna(row['energy']) else None, 
                    valence=row['valence'] if pd.notna(row['valence']) else None, 
                    tempo=row['tempo'] if pd.notna(row['tempo']) else None, 
                    liveness=row['liveness'] if pd.notna(row['liveness']) else None, 
                    acousticness=row['acousticness'] if pd.notna(row['acousticness']) else None, 
                    speechiness=row['speechiness'] if pd.notna(row['speechiness']) else None, 
                    instrumentalness=row['instrumentalness'] if pd.notna(row['instrumentalness']) else None,
                )
                
                # 3b. Ligar Artistas (Relação Muitos-para-Muitos)
                artist_ids_raw = row['artist_id'].strip('[]').replace("'", "").replace('"', "")
                artist_ids = [id.strip() for id in artist_ids_raw.split(',') if id.strip()]
                
                linked_artists = [artist_obj_map[id] for id in artist_ids if id in artist_obj_map]
                
                hit_song.artists.set(linked_artists)

        self.stdout.write(self.style.SUCCESS("Hit Songs importadas e ligadas aos artistas com sucesso."))
        self.stdout.write(self.style.SUCCESS("--- IMPORTAÇÃO DE DADOS CONCLUÍDA. PRÓXIMO: ANÁLISE ARS ---"))