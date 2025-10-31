# ars_network/management/commands/diagnose_communities.py

from django.core.management.base import BaseCommand
from ars_network.models import Artist, HitSong
import networkx as nx
import community.community_louvain as community
from collections import defaultdict
import json
import operator

class Command(BaseCommand):
    help = 'Roda o algoritmo Louvain e diagnostica o gênero dominante em cada comunidade.'

    def _rebuild_graph(self):
        # A mesma função de reconstrução de grafo usada para a visualização
        collaborations = defaultdict(lambda: defaultdict(int))
        hit_songs = HitSong.objects.prefetch_related('artists').all()
        
        for song in hit_songs:
            artist_ids = [artist.spotify_id for artist in song.artists.all()]
            for i in range(len(artist_ids)):
                for j in range(i + 1, len(artist_ids)):
                    id1, id2 = sorted((artist_ids[i], artist_ids[j]))
                    collaborations[id1][id2] += 1
        
        G = nx.Graph()
        for id1, inner_dict in collaborations.items():
            for id2, weight in inner_dict.items():
                G.add_edge(id1, id2, weight=weight)
        return G

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("--- DIAGNÓSTICO DE COMUNIDADES LOUVAIN ---"))
        
        G = self._rebuild_graph()
        artists = Artist.objects.all()
        
        # 1. Executar o Algoritmo Louvain
        self.stdout.write("Executando Louvain para identificar comunidades...")
        partition = community.best_partition(G, weight='weight', random_state=42) # Usar a mesma seed

        # 2. Mapear Gêneros por Comunidade
        community_genres = defaultdict(lambda: defaultdict(int))
        
        # Iterar sobre todos os artistas
        for artist in artists:
            community_id = partition.get(artist.spotify_id)
            if community_id is None:
                continue # Artistas isolados (grau 0)

            # Extração robusta de gêneros do campo 'genres' (string)
            try:
                genres_list_raw = json.loads(artist.genres.replace("'", "\""))
                genres_list = [g.strip().lower() for g in genres_list_raw if isinstance(g, str)]
            except (json.JSONDecodeError, AttributeError):
                genres_list = [g.strip().lower() for g in artist.genres.strip('[]').split(',') if g.strip()]

            # Contar a frequência de cada gênero dentro da comunidade
            for genre in genres_list:
                community_genres[community_id][genre] += 1

        # 3. Determinar o Gênero Dominante de Cada Comunidade
        self.stdout.write("\n--- RESULTADO DA INFERÊNCIA DE GÊNERO ---")
        
        results = {}
        for community_id, genre_counts in community_genres.items():
            
            # Encontra o gênero mais frequente (o dominante)
            dominant_genre = max(genre_counts.items(), key=operator.itemgetter(1))[0]
            
            # Conta o número de artistas na comunidade
            num_artists_in_community = sum(1 for cid in partition.values() if cid == community_id)

            results[community_id] = {
                'dominant_genre': dominant_genre,
                'num_artists': num_artists_in_community,
                'top_genres': [g[0] for g in sorted(genre_counts.items(), key=operator.itemgetter(1), reverse=True)[:3]]
            }
            
            self.stdout.write(f"Comunidade {community_id} ({num_artists_in_community} Artistas):")
            self.stdout.write(f"  Gênero Dominante: {dominant_genre.upper()}")
            self.stdout.write(f"  Top 3 Gêneros: {', '.join(results[community_id]['top_genres'])}")
        
        self.stdout.write(self.style.SUCCESS("\nDIAGNÓSTICO CONCLUÍDO. Use os IDs das Comunidades para criar a legenda de cores."))