from django.contrib import admin
from .models import Artist, HitSong # Importe seus modelos

# Register your models here.
# Registre os modelos
admin.site.register(Artist)
admin.site.register(HitSong)