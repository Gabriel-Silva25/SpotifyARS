from pathlib import Path
import pandas as pd

# ---------------------------
# Função para ler CSVs com separadores diferentes
# (Mantida apenas para Charts, onde o delimitador pode variar)
# ---------------------------
def read_csv_try(path):
    """Tenta ler um CSV com diferentes delimitadores (, ; \t)."""
    # Usado para charts, que pode ter um separador diferente por ano/região
    for sep in [',', ';', '\t']:
        try:
            return pd.read_csv(path, sep=sep, encoding='utf-8')
        except Exception:
            continue
    raise ValueError(f"Não consegui ler o arquivo {path}")

# ---------------------------
# Caminhos base
# ---------------------------
BASE_DIR = Path(__file__).resolve().parents[1]
RAW_DIR = BASE_DIR / "data" / "raw"
PROCESSED_DIR = BASE_DIR / "data" / "processed"
PROCESSED_DIR.mkdir(exist_ok=True)

print(f"Diretório de Processamento: {PROCESSED_DIR}")

# ---------------------------
# 1. Carregar Artists (Forçando Tabulação para corrigir leitura de colunas)
# ---------------------------
artists_file = RAW_DIR / "Artists" / "spotify_artists_info_complete.csv"

# CORREÇÃO CRÍTICA: Forçando o delimitador de tabulação (\t)
# O erro 'KeyError: artist_id' ocorreu porque a leitura inicial falhou e leu tudo em uma coluna.
df_artists = pd.read_csv(artists_file, sep='\t', encoding='utf-8') 

# Limpa espaços em branco nos nomes das colunas
df_artists.columns = df_artists.columns.str.strip()
print("\nArtistas carregados:", len(df_artists))
print(f"Colunas do DF Artists (após correção de delimitador): {df_artists.columns.tolist()}")

# Garante que o ID e Gêneros estejam no formato de string limpa
df_artists['artist_id'] = df_artists['artist_id'].astype(str).str.strip()
df_artists['genres'] = df_artists['genres'].astype(str).str.strip()

# ---------------------------
# 2. Carregar Charts BR 2017-2019
# ---------------------------
charts_br_dir = RAW_DIR / "Charts" / "br"
dfs_charts = []

# Iterar sobre pastas de ano e arquivos CSV
for year_folder in charts_br_dir.iterdir():
    if year_folder.is_dir() and year_folder.name.isdigit():
        for file in year_folder.glob("*.csv"):
            try:
                # Usando read_csv_try para charts (pode ser , ou ;)
                df = read_csv_try(file) 
                df["year"] = int(year_folder.name)
                dfs_charts.append(df)
            except Exception as e:
                print(f"Erro lendo {file}: {e}")

if not dfs_charts:
    raise FileNotFoundError("Nenhum arquivo de Charts BR encontrado. Verifique a estrutura de pastas.")

df_charts_br = pd.concat(dfs_charts, ignore_index=True)
# A coluna de ID de faixa no Charts é 'song_id' (limpa espaços para segurança)
df_charts_br.columns = df_charts_br.columns.str.strip()
print("Charts BR 2017-2019 carregados:", len(df_charts_br))

# ---------------------------
# 3. Carregar Hit Songs (Forçando Tabulação para corrigir leitura de colunas)
# ---------------------------
# Nome do arquivo conforme o README
hits_file = RAW_DIR / "Hit Songs" / "spotify_hits_dataset_complete.csv" 
# CORREÇÃO: Forçando o delimitador de tabulação (\t)
df_hits = pd.read_csv(hits_file, sep='\t', encoding='utf-8') 
df_hits.columns = df_hits.columns.str.strip() # Limpa espaços em branco
print("\nHit Songs carregadas (total):", len(df_hits))

# ---------------------------
# 4. Filtragem: Selecionar apenas as faixas que estiveram no Chart BR
# ---------------------------

# IDs Únicos de Faixas do Chart BR (usando a coluna 'song_id' do Charts)
# Garante que os IDs estejam limpos
track_ids_br = df_charts_br["song_id"].astype(str).str.strip().unique() 
print("IDs únicos de faixas que foram hit no BR (da Tabela Charts):", len(track_ids_br))

# Filtrar o DataFrame de Hit Songs pelas faixas do BR
df_hits_br = df_hits[df_hits["song_id"].isin(track_ids_br)].copy()
print("Hit Songs filtradas para o BR (com Audio Features):", len(df_hits_br))

# ---------------------------
# 5. Filtragem de Artistas
# ---------------------------

# Extrair TODOS os IDs de artistas (colaboradores) de todas as faixas BR
all_artist_ids_br = set()
for ids_string in df_hits_br["artist_id"].dropna():
    # Limpa caracteres de lista ([', ', ']) se existirem.
    cleaned_string = ids_string.strip('[]').replace("'", "").replace('"', "")
    ids_list = [id.strip() for id in cleaned_string.split(',') if id.strip()]
    all_artist_ids_br.update(ids_list)

print("IDs únicos de artistas dos hits BR:", len(all_artist_ids_br))

# Filtrar o DataFrame de Artistas (df_artists)
df_artists_br = df_artists[df_artists["artist_id"].isin(all_artist_ids_br)].copy()
# Agora esperamos um número > 0 aqui
print("Artistas filtrados para o BR:", len(df_artists_br))

# ---------------------------
# 6. Salvar as Versões FINAIS FILTRADAS (Prontas para o Django)
# ---------------------------
df_artists_br.to_parquet(PROCESSED_DIR / "artists_br.parquet", index=False)
df_hits_br.to_parquet(PROCESSED_DIR / "hitsongs_br.parquet", index=False)
df_charts_br.to_parquet(PROCESSED_DIR / "charts_br.parquet", index=False) 

print("\n--- PRÉ-PROCESSAMENTO CONCLUÍDO ---")
print("Artistas BR salvos em: artists_br.parquet")
print("Hit Songs BR salvas em: hitsongs_br.parquet")