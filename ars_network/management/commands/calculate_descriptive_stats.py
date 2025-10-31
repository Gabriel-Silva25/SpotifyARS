# ars_network/management/commands/calculate_descriptive_stats.py

from django.core.management.base import BaseCommand
from ars_network.models import HitSong
import pandas as pd
from datetime import datetime
import os

class Command(BaseCommand):
    help = 'Calcula e exporta estatísticas descritivas detalhadas para os atributos de HitSong (recorte Brasil).'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("--- INICIANDO CÁLCULO DE ESTATÍSTICAS DESCRITIVAS ---"))

        # 1. Exportar Dados do Django para o Pandas
        data = HitSong.objects.all().values(
            'popularity', 
            'danceability', 
            'energy', 
            'valence',
            'tempo'
        )
        df = pd.DataFrame(list(data))

        if df.empty:
            self.stdout.write(self.style.ERROR("Nenhum dado de HitSong encontrado."))
            return
        
        # 2. Calcular estatísticas básicas
        descriptive_stats = df.describe().transpose()

        # 3. Calcular estatísticas adicionais
        extra_stats = pd.DataFrame({
            'median': df.median(),
            'q1': df.quantile(0.25),
            'q3': df.quantile(0.75),
            'range': df.max() - df.min(),
            'coef_var (%)': (df.std() / df.mean()) * 100,
            'skewness': df.skew(),
            'kurtosis': df.kurtosis()
        }).round(3)

        # 4. Combinar todas as estatísticas
        combined_stats = pd.concat([
            descriptive_stats[['mean', 'std', 'min', 'max']], 
            extra_stats[['median', 'q1', 'q3', 'range', 'coef_var (%)', 'skewness', 'kurtosis']]
        ], axis=1)

        # 5. Renomear índices
        combined_stats.index = [
            'Popularidade', 
            'Dançabilidade', 
            'Energia', 
            'Valência', 
            'Tempo (BPM)'
        ]

        # 6. Calcular matriz de correlação
        corr_matrix = df.corr().round(3)

        # 7. Exibir no terminal (Markdown)
        self.stdout.write(self.style.SUCCESS(f"\nEstatísticas Descritivas da Amostra (N={len(df)}):\n"))
        self.stdout.write(combined_stats.round(3).to_markdown())
        self.stdout.write(self.style.SUCCESS("\nMatriz de Correlação entre Atributos:"))
        self.stdout.write(corr_matrix.to_markdown())

        # 8. Salvar em Excel
        output_dir = "data/descriptive_stats"
        os.makedirs(output_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = os.path.join(output_dir, f"estatisticas_hits_brasil_{timestamp}.xlsx")

        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            combined_stats.to_excel(writer, sheet_name='Estatísticas Descritivas')
            corr_matrix.to_excel(writer, sheet_name='Matriz de Correlação')

        self.stdout.write(self.style.SUCCESS(f"\nArquivo Excel gerado com sucesso em: {output_path}"))
        self.stdout.write(self.style.SUCCESS("\n--- FIM DO CÁLCULO DE ESTATÍSTICAS ---"))
