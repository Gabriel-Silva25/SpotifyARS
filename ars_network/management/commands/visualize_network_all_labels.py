# ars_network/management/commands/visualize_network_all_labels.py

from django.core.management.base import BaseCommand
from ars_network.models import Artist, HitSong
import networkx as nx
import community.community_louvain as community
import matplotlib.pyplot as plt
from collections import defaultdict
import matplotlib.colors as mcolors
from pathlib import Path
from django.conf import settings
import numpy as np

class Command(BaseCommand):
    help = 'Gera uma visualização de diagnóstico com 100% dos rótulos de artistas.'

    # Reutiliza a lógica de reconstrução de grafo e métricas
    def _rebuild_graph_and_get_metrics(self):
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
        
        partition = community.best_partition(G, weight='weight', random_state=42)
        
        # Obter métricas necessárias para visualização (tamanho e borda)
        artist_metrics = {a.spotify_id: a for a in artists_qs}
        return G, partition, artist_id_map, artist_metrics

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("--- INICIANDO VISUALIZAÇÃO DE DIAGNÓSTICO (100% RÓTULOS) ---"))
        
        G, partition, artist_id_map, artist_metrics = self._rebuild_graph_and_get_metrics()
        
        num_communities = max(partition.values()) + 1
        
        # Definição do limite de Intermediação para a borda vermelha
        betweenness_values = [artist_metrics[n].betweenness_centrality for n in G.nodes()]
        if betweenness_values:
            betweenness_threshold = max(0.001, np.percentile(betweenness_values, 90))
        else:
            betweenness_threshold = 0.001

        # 1. Preparação das Métricas de Visualização (Igual ao aprimorado)
        cmap = plt.cm.get_cmap('tab20', num_communities)
        node_colors = []
        node_sizes = []
        node_border_colors = []
        labels = {}
        
        for node in G.nodes():
            metrics = artist_metrics.get(node)
            if not metrics: continue

            # a. Tamanho do Nó (Baseado no Grau de Centralidade - Hubs)
            size = metrics.degree_centrality * 8000
            node_sizes.append(size)
            
            # b. Cor do Nó (Baseado na Comunidade)
            node_colors.append(cmap(partition.get(node, 0)))

            # c. Highlight (Cor de Borda) para as Pontes
            if metrics.betweenness_centrality >= betweenness_threshold:
                node_border_colors.append('red')
            else:
                node_border_colors.append(cmap(partition.get(node, 0)))
            
            # d. Rótulos (Ajuste para 100%): Rotula todos os nós
            labels[node] = metrics.name 

        # 2. Desenho do Grafo
        self.stdout.write(f"Rotulando 100% dos {G.number_of_nodes()} nós (Visibilidade Baixa Esperada)...")
        
        plt.figure(figsize=(25, 20)) # Aumenta a figura para tentar dar espaço aos rótulos
        
        pos = nx.spring_layout(G, k=0.18, iterations=50, seed=42) 

        # Desenha as Arestas
        edge_widths = [G[u][v]['weight'] * 0.5 for u, v in G.edges()]
        nx.draw_networkx_edges(G, pos, width=edge_widths, alpha=0.2, edge_color='gray')
        
        # Desenha os Nós
        nx.draw_networkx_nodes(G, pos, 
                               node_size=node_sizes, 
                               node_color=node_colors, 
                               edgecolors=node_border_colors,
                               linewidths=2, 
                               alpha=0.8)

        # Desenha os Rótulos (Fonte muito menor para tentar caber)
        nx.draw_networkx_labels(G, pos, labels=labels, font_size=5, font_weight='normal', alpha=0.8)

        # Legenda (Mantida para referência visual)
        plt.plot([], [], 'o', color='gray', alpha=0.7, markeredgecolor='red', markersize=10, linewidth=0, label='Ponte Crítica (Alta Intermediação)')
        plt.legend(scatterpoints=1, frameon=False, labelspacing=1, title="Destaque ARS", fontsize=10)


        plt.title(f"DIAGNÓSTICO: Rede de Colaboração (100% Rótulos) | Nós: {G.number_of_nodes()} | Arestas: {G.number_of_edges()}", fontsize=18)
        plt.axis('off')
        
        # 3. Salvamento
        BASE_DIR = settings.BASE_DIR
        output_dir = BASE_DIR / "data" / "analysis_output"
        output_dir.mkdir(exist_ok=True)
        
        output_path = output_dir / "artist_collaboration_network_100_labels.png"
        plt.tight_layout()
        plt.savefig(output_path, dpi=300)
        
        self.stdout.write(self.style.SUCCESS(f"\nGrafo de diagnóstico salvo com 100% rótulos em: {output_path}"))
        self.stdout.write(self.style.NOTICE("Use esta imagem apenas para referências internas, devido à alta poluição visual."))