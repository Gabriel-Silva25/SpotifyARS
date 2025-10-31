# ars_network/management/commands/visualize_network_by_genre.py

from django.core.management.base import BaseCommand
from ars_network.models import Artist, HitSong
import networkx as nx
import matplotlib.pyplot as plt
from collections import defaultdict
import matplotlib.colors as mcolors
from pathlib import Path
from django.conf import settings
import numpy as np
import json

class Command(BaseCommand):
    help = 'Gera a visualização da rede colorida pelo Gênero Dominante do artista.'

    def _rebuild_graph_and_get_metrics(self):
        # Reutiliza a lógica de construção de grafo e métricas
        collaborations = defaultdict(lambda: defaultdict(int))
        artists_qs = Artist.objects.all()
        artist_id_map = {a.spotify_id: a for a in artists_qs}

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
        
        # Simplesmente calcula betweenness e degree novamente (para o rótulo)
        betweenness = nx.betweenness_centrality(G, weight='weight')
        degree = nx.degree_centrality(G)
        
        # Atualiza as métricas no mapa para uso na visualização
        for artist in artists_qs:
            artist.betweenness_centrality = betweenness.get(artist.spotify_id, 0.0)
            artist.degree_centrality = degree.get(artist.spotify_id, 0.0)
            
        return G, artist_id_map, artists_qs
    
    def _get_dominant_genre(self, artist):
        # Pega o primeiro gênero da lista como o dominante
        genres_str = artist.genres.strip('[]').replace("'", "").replace('"', "")
        first_genre = genres_str.split(',')[0].strip().title()
        return first_genre if first_genre else "Sem Gênero"


    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("--- INICIANDO VISUALIZAÇÃO COLORIDA POR GÊNERO DOMINANTE ---"))
        
        G, artist_id_map, artists_qs = self._rebuild_graph_and_get_metrics()
        
        # 1. Mapeamento de Gêneros e Cores
        self.stdout.write("Mapeando Gênero Dominante e atribuindo cores...")
        
        # Define uma cor para cada Gênero Dominante único
        all_dominant_genres = sorted(list(set(self._get_dominant_genre(a) for a in artists_qs)))
        num_genres = len(all_dominant_genres)
        genre_to_id = {genre: i for i, genre in enumerate(all_dominant_genres)}
        
        # Usa um mapa de cores maior, se necessário
        cmap = plt.cm.get_cmap('gist_rainbow', num_genres)

        # 2. Preparação das Métricas de Visualização
        
        # Define o limite para a borda vermelha (top 10% das pontes)
        betweenness_values = [a.betweenness_centrality for a in artists_qs]
        betweenness_threshold = max(0.001, np.percentile(betweenness_values, 90))
        
        node_sizes, node_colors, node_border_colors, labels = [], [], [], {}
        
        for node in G.nodes():
            artist = artist_id_map.get(node)
            if not artist: continue
                
            dominant_genre = self._get_dominant_genre(artist)
            genre_id = genre_to_id[dominant_genre]

            # a. Tamanho do Nó (Centralidade de Grau)
            size = artist.degree_centrality * 8000
            node_sizes.append(size)
            
            # b. Cor do Nó (Cor Focada no Gênero)
            node_colors.append(cmap(genre_id))

            # c. Highlight (Borda Vermelha) para as Pontes
            if artist.betweenness_centrality >= betweenness_threshold:
                node_border_colors.append('red')
                # Rotula todas as pontes importantes
                labels[node] = artist.name
            else:
                # Rotula apenas hubs de alto grau
                if size > np.percentile(node_sizes, 95):
                    labels[node] = artist.name
                node_border_colors.append(cmap(genre_id)) 

        # 3. Desenho do Grafo
        self.stdout.write(f"Desenhando o Grafo com {num_genres} cores distintas de Gênero...")
        
        plt.figure(figsize=(25, 20))
        
        pos = nx.spring_layout(G, k=0.18, iterations=50, seed=42) 

        # Desenha Arestas e Nós (Lógica de desenho é a mesma)
        edge_widths = [G[u][v]['weight'] * 0.5 for u, v in G.edges()]
        nx.draw_networkx_edges(G, pos, width=edge_widths, alpha=0.15, edge_color='gray')
        
        nx.draw_networkx_nodes(G, pos, 
                               node_size=node_sizes, 
                               node_color=node_colors, 
                               edgecolors=node_border_colors,
                               linewidths=2, 
                               alpha=0.8)

        nx.draw_networkx_labels(G, pos, labels=labels, font_size=9, font_weight='bold')

        # 4. Legenda de Gêneros e Salvamento
        
        # Cria Handles e Rótulos para a legenda de cores de Gênero
        legend_handles = []
        for genre, i in genre_to_id.items():
            legend_handles.append(plt.Line2D([0], [0], marker='o', color='w', 
                                            label=f'{genre}', markersize=10, 
                                            markerfacecolor=cmap(i)))
        
        # Adiciona o rótulo de Ponte
        legend_handles.append(plt.Line2D([0], [0], marker='o', color='w', 
                                        label='Ponte Crítica (Alta Intermediação)', markersize=10, 
                                        markerfacecolor='gray', markeredgecolor='red', markeredgewidth=2))


        plt.legend(handles=legend_handles, title="Gênero Dominante & Destaque ARS", 
                   loc='upper right', bbox_to_anchor=(1.2, 1), ncol=1, fontsize=10)

        plt.title(f"Rede de Colaboração (Colorida por Gênero Dominante) | BR (2017-2019)", fontsize=18)
        plt.axis('off')
        
        # Salvamento
        BASE_DIR = settings.BASE_DIR
        output_dir = BASE_DIR / "data" / "analysis_output"
        output_dir.mkdir(exist_ok=True)
        
        output_path = output_dir / "artist_collaboration_network_by_genre.png"
        plt.tight_layout()
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        
        self.stdout.write(self.style.SUCCESS(f"\nGrafo colorido por Gênero Dominante salvo em: {output_path}"))
        self.stdout.write(self.style.NOTICE("A cor de cada nó representa o primeiro gênero listado pelo Spotify."))