# ars_network/management/commands/analyze_network.py

from django.core.management.base import BaseCommand
from django.db import transaction
from ars_network.models import Artist, HitSong
import networkx as nx
import json
import numpy as np
from collections import defaultdict 

class Command(BaseCommand):
    help = 'Constrói a rede de colaboração, calcula as métricas ARS (Centralidade, IHG) e salva no banco.'

    def _calculate_ihg(self, hit_song):
        """Calcula o Índice de Heterogeneidade de Gênero (IHG) para uma HitSong."""
        
        # 1. Obter todos os gêneros únicos de todos os artistas
        all_genres = set()
        num_artists = 0
        
        # O prefetch_related garante que os dados do artista já estão na memória
        for artist in hit_song.artists.all():
            num_artists += 1
            
            # O campo 'genres' é uma string formatada como lista (ex: "['pop', 'dance pop']")
            # Tentativa robusta de extrair a lista de gêneros
            try:
                # Usa json.loads para converter a string de lista em uma lista Python
                genres_list_raw = json.loads(artist.genres.replace("'", "\""))
                # Certifica que é uma lista de strings
                genres_list = [g.strip() for g in genres_list_raw if isinstance(g, str)]
            except (json.JSONDecodeError, AttributeError):
                # Fallback: Se não for um formato JSON válido, trata como string separada por vírgula
                genres_list = [g.strip() for g in artist.genres.strip('[]').split(',') if g.strip()]
            
            all_genres.update(genres_list)

        # 2. Cálculo do IHG
        # IHG = (Número de Gêneros Únicos) / (Número de Artistas Colaboradores)
        if num_artists > 0:
            return len(all_genres) / num_artists
        return 0.0

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("--- INICIANDO ANÁLISE ARS E CÁLCULO DE MÉTRICAS ---"))
        
        # 1. Preparação: Mapear colaborações
        collaborations = defaultdict(lambda: defaultdict(int)) # {artist1: {artist2: weight}}
        artist_id_map = {artist.spotify_id: artist for artist in Artist.objects.all()}

        if not artist_id_map:
            self.stdout.write(self.style.ERROR("Nenhum artista encontrado no banco de dados. Importe os dados primeiro."))
            return

        # Busca todas as HitSongs e seus artistas relacionados de uma vez
        hit_songs = HitSong.objects.prefetch_related('artists').all()
        
        self.stdout.write(f"Construindo rede a partir de {len(hit_songs)} hits...")

        # 2. Construção da Rede de Colaboração (Grafo NetworkX)
        for song in hit_songs:
            artist_ids = [artist.spotify_id for artist in song.artists.all()]
            
            # Cria arestas para todas as combinações (pares) de artistas na música
            for i in range(len(artist_ids)):
                for j in range(i + 1, len(artist_ids)):
                    id1, id2 = sorted((artist_ids[i], artist_ids[j]))
                    
                    # Pondera a aresta pelo número de colaborações (MGD+ Methodology)
                    collaborations[id1][id2] += 1
        
        # Cria o grafo
        G = nx.Graph()
        
        for id1, inner_dict in collaborations.items():
            for id2, weight in inner_dict.items():
                G.add_edge(id1, id2, weight=weight)
        
        self.stdout.write(f"Rede de Colaboração construída: {G.number_of_nodes()} nós, {G.number_of_edges()} arestas.")

        # 3. Cálculo das Métricas de Centralidade
        self.stdout.write("Calculando Centralidade de Intermediação (Betweenness) e Grau...")

        # Centralidade de Intermediação (Betweenness): Peso=weight considera a força da colaboração
        betweenness = nx.betweenness_centrality(G, weight='weight')
        # Centralidade de Grau (Degree): Quantos colaboradores o artista tem
        degree = nx.degree_centrality(G)

        # 4. Persistência: Artistas (Nós) - Salvando as métricas de Centralidade
        self.stdout.write("Salvando Centralidades no modelo Artist...")
        with transaction.atomic():
            for artist_id, artist_obj in artist_id_map.items():
                
                # Campos vazios no Admin (serão preenchidos aqui)
                artist_obj.betweenness_centrality = betweenness.get(artist_id, 0.0)
                artist_obj.degree_centrality = degree.get(artist_id, 0.0)
                
                # Opcional, mas útil: Contagem de Hits e Colaborações (simples, mas robusto)
                artist_hits = hit_songs.filter(artists=artist_obj)
                artist_obj.num_hits = artist_hits.count()
                # Collab hits: hits onde o artista participou E havia mais de um artista
                artist_obj.num_collab_hits = artist_hits.filter(is_collaboration=True).count()
                
                artist_obj.save()
        
        self.stdout.write("Centralidades e contagem de Hits salvas no modelo Artist.")

        # 5. Cálculo e Persistência: HitSongs (IHG e Centralidade Média)
        self.stdout.write("Calculando IHG e Média de Intermediação para HitSongs...")
        
        # Re-carrega os objetos Artist com as novas centralidades salvas
        artists_with_metrics = {a.spotify_id: a for a in Artist.objects.all()}

        with transaction.atomic():
            for song in hit_songs:
                
                # a. Calcular IHG (Heterogeneidade de Gênero)
                ihg_value = self._calculate_ihg(song)
                
                # b. Calcular Intermediação Média dos Colaboradores
                total_betweenness = 0.0
                num_collaborators = 0
                
                for artist in song.artists.all():
                    # Usa o valor persistido que acabamos de calcular
                    total_betweenness += artists_with_metrics.get(artist.spotify_id, Artist()).betweenness_centrality
                    num_collaborators += 1
                
                # Evita divisão por zero
                avg_betweenness = total_betweenness / num_collaborators if num_collaborators > 0 else 0.0
                
                # Opcional: Calcula a soma da popularidade, para análise
                song.mean_popularity = song.popularity
                
                # c. Persistir na HitSong
                song.genre_heterogeneity_index = ihg_value
                song.avg_artist_betweenness = avg_betweenness
                song.save()

        self.stdout.write("IHG e Centralidade Média salvas no modelo HitSong.")
        self.stdout.write(self.style.SUCCESS("--- ANÁLISE ARS CONCLUÍDA. DADOS PRONTOS PARA REGRESSÃO! ---"))