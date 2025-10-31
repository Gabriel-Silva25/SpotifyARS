# ars_network/management/commands/visualize_network.py (VERSÃO APRIMORADA)

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
    help = 'Constrói e visualiza o grafo de colaboração com detecção de comunidades e rótulos aprimorados.'

    # Usamos o mesmo método de construção de rede (omiti para concisão, assumindo que já está definido)
    def _rebuild_graph(self):
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
        self.stdout.write(self.style.SUCCESS("--- INICIANDO VISUALIZAÇÃO DA REDE DE COLABORAÇÃO APRIMORADA ---"))
        
        G = self._rebuild_graph()
        
        artists = Artist.objects.all()
        artist_metrics = {a.spotify_id: a for a in artists}

        # 1. Detecção de Comunidades (Louvain)
        partition = community.best_partition(G, weight='weight')
        num_communities = max(partition.values()) + 1
        
        # 2. Preparação das Métricas de Visualização
        
        # Mapa de cores e tamanhos
        cmap = plt.cm.get_cmap('tab20', num_communities)
        
        # Define o limite mínimo para ser considerado um "hub" ou "ponte" relevante
        # Usaremos o percentil 90 (os 10% mais altos) para Intermediação
        betweenness_values = [artist_metrics[n].betweenness_centrality for n in G.nodes()]
        if betweenness_values:
            betweenness_threshold = max(0.001, np.percentile(betweenness_values, 90))
        else:
            betweenness_threshold = 0.001
        
        # Listas de nós, rótulos e cores
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

            # c. Highlight (Cor de Borda) para as Pontes (Intermediação)
            # Se a Centralidade de Intermediação for alta (top 10%), pinta a borda de vermelho
            if metrics.betweenness_centrality >= betweenness_threshold:
                node_border_colors.append('red')
                # Rotula todas as pontes e os hubs importantes
                labels[node] = metrics.name
            else:
                node_border_colors.append(cmap(partition.get(node, 0))) # Usa a cor da comunidade
            
            # d. Rótulos Adicionais: Adiciona rótulo para hubs muito grandes (top 5% do Grau)
            if size > np.percentile(node_sizes, 95):
                labels[node] = metrics.name

        # 3. Desenho do Grafo
        self.stdout.write(f"Rotulando {len(labels)} nós (Pontes e Hubs Top)...")
        
        plt.figure(figsize=(20, 16))
        
        # Layout (ajuste leve no k para separar um pouco mais)
        pos = nx.spring_layout(G, k=0.18, iterations=50, seed=42) 

        # Desenha as Arestas
        edge_widths = [G[u][v]['weight'] * 0.5 for u, v in G.edges()]
        nx.draw_networkx_edges(G, pos, 
                               width=edge_widths, 
                               alpha=0.3, 
                               edge_color='gray')
        
        # Desenha os Nós (com o Highlight de Borda)
        # O contorno (linewidth) e a cor de borda (edgecolor) destacam as pontes
        nx.draw_networkx_nodes(G, pos, 
                               node_size=node_sizes, 
                               node_color=node_colors, 
                               edgecolors=node_border_colors,
                               linewidths=2, # Borda mais grossa para destacar
                               alpha=0.8)

        # Desenha os Rótulos
        nx.draw_networkx_labels(G, pos, labels=labels, font_size=9, font_weight='bold')

        # Cria a legenda manual para o highlight
        self.stdout.write("Criando legenda para o destaque das 'Pontes' (Intermediação)...")
        plt.plot([], [], 'o', color='gray', alpha=0.7, markeredgecolor='red', markersize=10, linewidth=0, label='Ponte Crítica (Alta Intermediação)')
        plt.legend(scatterpoints=1, frameon=False, labelspacing=1, title="Destaque ARS", fontsize=12)


        plt.title(f"Rede de Colaboração de Artistas BR (2017-2019) | Nós: {G.number_of_nodes()} | Arestas: {G.number_of_edges()}", fontsize=16)
        plt.axis('off')
        
        # 4. Salvamento
        BASE_DIR = settings.BASE_DIR
        output_dir = BASE_DIR / "data" / "analysis_output"
        output_dir.mkdir(exist_ok=True)
        
        output_path = output_dir / "artist_collaboration_network_br_aprimorado.png"
        plt.tight_layout()
        plt.savefig(output_path, dpi=300)
        
        self.stdout.write(self.style.SUCCESS(f"\nGrafo aprimorado salvo com sucesso em: {output_path}"))
        self.stdout.write(self.style.NOTICE("Nós com borda VERMELHA são as 'Pontes' (Alta Centralidade de Intermediação)."))