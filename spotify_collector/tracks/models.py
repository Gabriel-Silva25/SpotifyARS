from django.db import models

class Track(models.Model):
    spotify_id = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=255)
    artist = models.CharField(max_length=255)
    album = models.CharField(max_length=255)
    popularity = models.IntegerField()
    tempo = models.FloatField(null=True)
    valence = models.FloatField(null=True)
    speechiness = models.FloatField(null=True)
    danceability = models.FloatField(null=True)
    liveness = models.FloatField(null=True)
    velocity = models.FloatField(null=True)  # Taxa de mudança da popularidade
    mean_popularity = models.FloatField(null=True)
    median_popularity = models.FloatField(null=True)
    std_popularity = models.FloatField(null=True)  # Desvio padrão da popularidade
    retrieval_frequency = models.IntegerField(null=True)  # Frequência de atualização
    trend = models.CharField(max_length=10, choices=[('up', 'Up'), ('down', 'Down'), ('stable', 'Stable')])
    genres = models.TextField(blank=True, null=True) # Permite que o campo seja vazio
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f'{self.name} by {self.artist}'