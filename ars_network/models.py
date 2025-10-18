from django.db import models

# Create your models here.

# ars_network/models.py

# O NÓ DA REDE: ARTISTAS
class Artist(models.Model):
    # spotify_id como chave primária é uma boa prática
    spotify_id = models.CharField(max_length=100, unique=True, primary_key=True) 
    name = models.CharField(max_length=255)
    
    # Gêneros do artista (CRÍTICO para a hipótese de "pontes")
    # Gêneros são extraídos do artista, não da faixa [cite: 381]
    genres = models.CharField(max_length=1024, default="", blank=True) 
    
    # Métricas do artista:
    artist_popularity = models.IntegerField(null=True, verbose_name="Popularidade do Artista") 
    num_hits = models.IntegerField(null=True, verbose_name="Número de Hits")
    num_collab_hits = models.IntegerField(null=True, verbose_name="Hits em Colaboração")

    # Métricas da ARS a ser calculada
    betweenness_centrality = models.FloatField(null=True, verbose_name="Centralidade de Intermediação")
    degree_centrality = models.FloatField(null=True, verbose_name="Centralidade de Grau")
    
    def __str__(self):
        return self.name

# A FAIXA/HIT MUSICAL
class HitSong(models.Model):
    # ID principal e detalhes básicos da faixa
    spotify_id = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=255)
    album = models.CharField(max_length=255, default="", blank=True)
    popularity = models.IntegerField(verbose_name="Popularidade da Faixa") # O seu y
    release_date = models.DateField(null=True)
    explicit = models.BooleanField(default=False)
    
    # RELAÇÃO M:M com artistas (captura a colaboração)
    artists = models.ManyToManyField(Artist, related_name='hit_songs')
    is_collaboration = models.BooleanField(default=False, verbose_name="É Colaboração")
    
    # CAMPO DE FOCO GEOGRÁFICO
    # Embora não seja um campo do MGD+, é útil para fixar o escopo do projeto (Brasil)
    market_of_origin = models.CharField(max_length=100, default='BR - Brasil', verbose_name="Mercado-alvo da Análise")
    
    # Atributos de Áudio (para contextualizar as comunidades)
    danceability = models.FloatField(null=True)
    energy = models.FloatField(null=True)
    valence = models.FloatField(null=True)
    tempo = models.FloatField(null=True)
    liveness = models.FloatField(null=True)
    acousticness = models.FloatField(null=True)
    speechiness = models.FloatField(null=True)
    instrumentalness = models.FloatField(null=True)
    
    # Métricas da ARS e Hipótese
    genre_heterogeneity_index = models.FloatField(null=True, verbose_name="Índice de Heterogeneidade de Gênero") 
    avg_artist_betweenness = models.FloatField(null=True, verbose_name="Média da Intermediação dos Artistas") 
    
    # Campos estatísticos (que você já tinha)
    created_at = models.DateTimeField(auto_now_add=True)
    velocity = models.FloatField(null=True)  
    mean_popularity = models.FloatField(null=True)
    std_popularity = models.FloatField(null=True)  
    trend = models.CharField(max_length=10, default='stable')

    def __str__(self):
        return f'{self.name} ({self.market_of_origin})'
