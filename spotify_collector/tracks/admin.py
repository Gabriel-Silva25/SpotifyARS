from django.contrib import admin
from .models import Track # 1. Importe seu modelo 'Track'

# 2. Registre o modelo na "lista de convidados" do Admin
admin.site.register(Track)