# ars_network/management/commands/analyze_regression.py

from django.core.management.base import BaseCommand
from ars_network.models import HitSong
import pandas as pd
import statsmodels.formula.api as smf

class Command(BaseCommand):
    help = 'Executa a Regressão Linear Múltipla para validar a hipótese ARS.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("--- INICIANDO ANÁLISE DE REGRESSÃO E VALIDAÇÃO DE HIPÓTESE ---"))

        # 1. Exportar Dados do Django para o Pandas
        # Seleciona as variáveis cruciais da tabela HitSong
        # Variável Dependente (Y): popularity
        # Variáveis Preditivas (X): IHG e avg_artist_betweenness
        # Variáveis de Controle: danceability e energy (exemplos de atributos de áudio)
        
        data = HitSong.objects.all().values(
            'popularity', 
            'avg_artist_betweenness', 
            'genre_heterogeneity_index', 
            'danceability', 
            'energy'
        )
        df = pd.DataFrame(data)

        if df.empty:
            self.stdout.write(self.style.ERROR("Nenhum dado de HitSong encontrado. A regressão não pode ser executada."))
            return
        
        # 2. Preparar e Limpar os Dados para a Regressão
        # A regressão não lida com valores NaN (ausentes), então removemos as linhas com NaN
        df_clean = df.dropna()
        
        self.stdout.write(f"Dados limpos para regressão: {len(df_clean)} de {len(df)} observações.")

        # 3. Definição do Modelo de Regressão (OLS - Ordinary Least Squares)
        # Y ~ X1 + X2 + X3 + ...
        # Hipótese principal é que avg_artist_betweenness tem um coeficiente positivo (β1 > 0)
        
        formula = 'popularity ~ avg_artist_betweenness + genre_heterogeneity_index + danceability + energy'
        
        # 4. Execução do Modelo
        self.stdout.write(f"Executando modelo: {formula}")
        try:
            model = smf.ols(formula=formula, data=df_clean)
            results = model.fit()

            # 5. Apresentação dos Resultados
            self.stdout.write(self.style.SUCCESS("\n--- RESULTADOS DA REGRESSÃO ---"))
            self.stdout.write(results.summary().as_text())

            self.stdout.write(self.style.SUCCESS("\n--- VALIDAÇÃO DA HIPÓTESE ---"))
            
            # Análise do Coeficiente da Variável de Intermediação
            avg_betweenness_coef = results.params['avg_artist_betweenness']
            avg_betweenness_pvalue = results.pvalues['avg_artist_betweenness']
            
            # Checa se o coeficiente é positivo e estatisticamente significativo (p-value < 0.05)
            if avg_betweenness_coef > 0 and avg_betweenness_pvalue < 0.05:
                self.stdout.write(self.style.SUCCESS(f"✅ HIPÓTESE CONFIRMADA!"))
                self.stdout.write(f"O coeficiente da Intermediação ({avg_betweenness_coef:.4f}) é positivo e significativo (p={avg_betweenness_pvalue:.4f}).")
                self.stdout.write("A posição do artista como 'ponte' na rede de colaboração AUMENTA a popularidade da música.")
            else:
                self.stdout.write(self.style.WARNING(f"❌ HIPÓTESE REFUTADA ou NÃO SIGNIFICATIVA."))
                self.stdout.write(f"O coeficiente da Intermediação ({avg_betweenness_coef:.4f}) não é significativo ou é negativo.")
                
            # Análise do Coeficiente da Heterogeneidade de Gênero (IHG)
            ihg_coef = results.params['genre_heterogeneity_index']
            ihg_pvalue = results.pvalues['genre_heterogeneity_index']
            
            if ihg_coef > 0 and ihg_pvalue < 0.05:
                 self.stdout.write(self.style.SUCCESS(f"✅ Heterogeneidade de Gênero Aumenta a Popularidade."))
                 self.stdout.write(f"O cruzamento de gêneros (IHG={ihg_coef:.4f}) contribui de forma independente para a viralidade.")

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Ocorreu um erro durante a regressão: {e}"))
            self.stdout.write(self.style.NOTICE("Verifique se há variância zero (todos os valores são iguais) em alguma coluna."))


        self.stdout.write(self.style.SUCCESS("\n--- FIM DA ANÁLISE ESTATÍSTICA ---"))