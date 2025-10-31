# ars_network/management/commands/visualize_network_zoom.py (VERSÃO PARA RECORTES)

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
    help = 'Gera visualizações da rede colorida por Gênero Dominante, incluindo zooms para apresentação.'

    def _rebuild_graph_and_get_metrics(self):
        # ... (Mantém a mesma lógica de reconstrução do grafo e cálculo de betweenness/degree) ...
        # (Seu código original desta parte deve ser mantido aqui)
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
        
        betweenness = nx.betweenness_centrality(G, weight='weight')
        degree = nx.degree_centrality(G)
        
        for artist in artists_qs:
            artist.betweenness_centrality = betweenness.get(artist.spotify_id, 0.0)
            artist.degree_centrality = degree.get(artist.spotify_id, 0.0)
            
        return G, artist_id_map, artists_qs
    
    def _get_dominant_genre(self, artist):
        genres_str = artist.genres.strip('[]').replace("'", "").replace('"', "")
        first_genre = genres_str.split(',')[0].strip().title()
        return first_genre if first_genre else "Sem Gênero"

    def _draw_graph_segment(self, G, pos, artist_id_map, artists_qs, ax, title_suffix, xlim=None, ylim=None):
        # (Mantém a mesma lógica de preparação de cores e tamanhos de nós)
        all_dominant_genres = sorted(list(set(self._get_dominant_genre(a) for a in artists_qs)))
        num_genres = len(all_dominant_genres)
        genre_to_id = {genre: i for i, genre in enumerate(all_dominant_genres)}
        cmap = plt.cm.get_cmap('gist_rainbow', num_genres)

        betweenness_values = [a.betweenness_centrality for a in artists_qs]
        betweenness_threshold = max(0.001, np.percentile(betweenness_values, 90))
        
        node_sizes, node_colors, node_border_colors, labels = [], [], [], {}
        
        # Filtra os nós que estão dentro do recorte para desenhar apenas eles
        nodes_to_draw = []
        for node in G.nodes():
            artist_pos = pos[node]
            if xlim and (artist_pos[0] < xlim[0] or artist_pos[0] > xlim[1]):
                continue
            if ylim and (artist_pos[1] < ylim[0] or artist_pos[1] > ylim[1]):
                continue
            nodes_to_draw.append(node)

        for node in G.nodes():
            artist = artist_id_map.get(node)
            if not artist: continue
                
            dominant_genre = self._get_dominant_genre(artist)
            genre_id = genre_to_id[dominant_genre]

            size = artist.degree_centrality * 8000
            node_sizes.append(size)
            node_colors.append(cmap(genre_id))

            if artist.betweenness_centrality >= betweenness_threshold:
                node_border_colors.append('red')
                labels[node] = artist.name
            else:
                if size > np.percentile([s for s in node_sizes if s > 0], 95) if node_sizes else 0:
                     labels[node] = artist.name
                node_border_colors.append(cmap(genre_id)) 

        # Desenha apenas as arestas e nós que estão dentro do recorte
        edges_to_draw = []
        edge_widths = []
        for u, v in G.edges():
            if u in nodes_to_draw and v in nodes_to_draw:
                edges_to_draw.append((u, v))
                edge_widths.append(G[u][v]['weight'] * 0.5)

        nx.draw_networkx_edges(G, pos, ax=ax, edgelist=edges_to_draw, width=edge_widths, alpha=0.15, edge_color='gray')
        
        # Garante que as listas de cores/tamanhos/bordas tenham o mesmo tamanho dos nós desenhados
        node_sizes_filtered = [s for i, s in enumerate(node_sizes) if list(G.nodes())[i] in nodes_to_draw]
        node_colors_filtered = [c for i, c in enumerate(node_colors) if list(G.nodes())[i] in nodes_to_draw]
        node_border_colors_filtered = [c for i, c in enumerate(node_border_colors) if list(G.nodes())[i] in nodes_to_draw]
        
        nx.draw_networkx_nodes(G, pos, ax=ax, nodelist=nodes_to_draw,
                               node_size=node_sizes_filtered, 
                               node_color=node_colors_filtered, 
                               edgecolors=node_border_colors_filtered,
                               linewidths=2, alpha=0.8)

        # Filtra os rótulos para mostrar apenas os nós dentro do recorte
        labels_filtered = {n: l for n, l in labels.items() if n in nodes_to_draw}
        nx.draw_networkx_labels(G, pos, ax=ax, labels=labels_filtered, font_size=9, font_weight='bold')

        ax.set_title(title_suffix)
        ax.set_axis_off()

        # Configura os limites se forem fornecidos
        if xlim:
            ax.set_xlim(xlim)
        if ylim:
            ax.set_ylim(ylim)

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("--- INICIANDO GERAÇÃO DE VISUALIZAÇÕES COM ZOOMS ---"))
        
        G, artist_id_map, artists_qs = self._rebuild_graph_and_get_metrics()
        
        # Calcula o layout uma única vez para manter a consistência
        pos = nx.spring_layout(G, k=0.18, iterations=50, seed=42) 

        # -- Geração do Grafo Completo --
        plt.figure(figsize=(25, 20))
        ax_full = plt.gca()
        self._draw_graph_segment(G, pos, artist_id_map, artists_qs, ax_full, 
                                 "Rede de Colaboração (Colorida por Gênero Dominante) | BR (2017-2019)")
        
        # 4. Legenda de Gêneros e Salvamento
        all_dominant_genres = sorted(list(set(self._get_dominant_genre(a) for a in artists_qs)))
        num_genres = len(all_dominant_genres)
        genre_to_id = {genre: i for i, genre in enumerate(all_dominant_genres)}
        cmap = plt.cm.get_cmap('gist_rainbow', num_genres)

        legend_handles = []
        for genre, i in genre_to_id.items():
            legend_handles.append(plt.Line2D([0], [0], marker='o', color='w', 
                                            label=f'{genre}', markersize=10, 
                                            markerfacecolor=cmap(i)))
        legend_handles.append(plt.Line2D([0], [0], marker='o', color='w', 
                                        label='Ponte Crítica (Alta Intermediação)', markersize=10, 
                                        markerfacecolor='gray', markeredgecolor='red', markeredgewidth=2))
        plt.legend(handles=legend_handles, title="Gênero Dominante & Destaque ARS", 
                   loc='upper right', bbox_to_anchor=(1.2, 1), ncol=1, fontsize=10)
        
        BASE_DIR = settings.BASE_DIR
        output_dir = BASE_DIR / "data" / "analysis_output"
        output_dir.mkdir(exist_ok=True)
        
        output_path_full = output_dir / "artist_collaboration_network_by_genre_full.png"
        plt.tight_layout()
        plt.savefig(output_path_full, dpi=300, bbox_inches='tight')
        self.stdout.write(self.style.SUCCESS(f"\nGrafo COMPLETO colorido por Gênero Dominante salvo em: {output_path_full}"))


        # -- Geração dos Zooms --
        # Coordenadas aproximadas para o centro (Anitta, Marília, Alok, Safadão)
        # Você pode ajustar esses valores com base no grafo completo para focar melhor
        # Exemplo: xlim = (0.0, 0.5), ylim = (0.2, 0.7)
        
        # Encontra as coordenadas de Anitta, para centralizar o zoom no núcleo
        anitta_pos = pos.get(next(a.spotify_id for a in artists_qs if a.name == 'Anitta'), np.array([0.0, 0.0]))
        
        # Ajusta os limites para focar em Anitta e seus vizinhos
        zoom_center_xlim = (anitta_pos[0] - 0.4, anitta_pos[0] + 0.4) 
        zoom_center_ylim = (anitta_pos[1] - 0.4, anitta_pos[1] + 0.4)

        plt.figure(figsize=(15, 12))
        ax_center = plt.gca()
        self._draw_graph_segment(G, pos, artist_id_map, artists_qs, ax_center, 
                                 "Núcleo da Rede: Anitta e Pontes Críticas (Zoom)", 
                                 xlim=zoom_center_xlim, ylim=zoom_center_ylim)
        plt.legend(handles=legend_handles, title="Gênero Dominante & Destaque ARS", 
                   loc='upper right', bbox_to_anchor=(1.2, 1), ncol=1, fontsize=10)
        output_path_center_zoom = output_dir / "artist_collaboration_network_center_zoom.png"
        plt.tight_layout()
        plt.savefig(output_path_center_zoom, dpi=300, bbox_inches='tight')
        self.stdout.write(self.style.SUCCESS(f"Zoom do NÚCLEO da Rede salvo em: {output_path_center_zoom}"))


        # Coordenadas aproximadas para o cluster Sertanejo (canto superior esquerdo)
        # Pode ser necessário ajustar com base no grafo completo
        # Exemplo: xlim = (-1.0, -0.4), ylim = (0.5, 1.0)
        
        # Encontra as coordenadas de Marília Mendonça como referência para o cluster sertanejo
        marilia_pos = pos.get(next(a.spotify_id for a in artists_qs if a.name == 'Marília Mendonça'), np.array([0.0, 0.0]))
        
        zoom_sertanejo_xlim = (marilia_pos[0] - 0.3, marilia_pos[0] + 0.3)
        zoom_sertanejo_ylim = (marilia_pos[1] - 0.3, marilia_pos[1] + 0.3)

        plt.figure(figsize=(15, 12))
        ax_sertanejo = plt.gca()
        self._draw_graph_segment(G, pos, artist_id_map, artists_qs, ax_sertanejo, 
                                 "Cluster Sertanejo (Zoom)",
                                 xlim=zoom_sertanejo_xlim, ylim=zoom_sertanejo_ylim)
        plt.legend(handles=legend_handles, title="Gênero Dominante & Destaque ARS", 
                   loc='upper right', bbox_to_anchor=(1.2, 1), ncol=1, fontsize=10)
        output_path_sertanejo_zoom = output_dir / "artist_collaboration_network_sertanejo_zoom.png"
        plt.tight_layout()
        plt.savefig(output_path_sertanejo_zoom, dpi=300, bbox_inches='tight')
        self.stdout.write(self.style.SUCCESS(f"Zoom do CLUSTER SERTANEJO salvo em: {output_path_sertanejo_zoom}"))

        self.stdout.write(self.style.SUCCESS("\n--- GERAÇÃO DE VISUALIZAÇÕES CONCLUÍDA ---"))