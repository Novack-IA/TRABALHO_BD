import pandas as pd
import psycopg2
import duckdb
import time

# --- NOME DO ARQUIVO DO NOSSO DATA WAREHOUSE LOCAL ---
ARQUIVO_DW = 'book_crossing_dw.duckdb'

# --- 1. ETAPA DE EXTRAÇÃO (EXTRACT) ---
def extrair_dados_do_postgres():
    """Conecta ao PostgreSQL e extrai as tabelas para DataFrames."""
    print("Conectando ao PostgreSQL para extrair dados...")
    try:
        conn = psycopg2.connect(host="localhost", port="5432", dbname="book_crossing_db", user="user", password="password")
        
        df_users = pd.read_sql("SELECT * FROM Usuarios", conn)
        df_books = pd.read_sql("SELECT * FROM Livros", conn)
        # Extrai apenas avaliações explícitas (nota > 0)
        df_ratings = pd.read_sql("SELECT * FROM Avaliacoes WHERE avaliacao > 0", conn)
        
        conn.close()
        print("✅ Dados extraídos com sucesso do PostgreSQL!")
        return df_users, df_books, df_ratings
    except Exception as e:
        print(f"❌ Erro ao extrair dados do PostgreSQL: {e}")
        return None, None, None

# --- 2. ETAPA DE TRANSFORMAÇÃO (TRANSFORM) ---
def transformar_dados(df_users, df_books, df_ratings):
    """Transforma os dados brutos em um modelo de esquema estrela."""
    print("\nIniciando transformação dos dados para o modelo estrela...")
    
    # Transformando a dimensão de Usuários
    print("  - Criando dim_usuarios...")
    dim_usuarios = df_users[['id_usuario', 'idade']].copy()
    dim_usuarios['pais'] = df_users['localizacao'].str.split(',').str[-1].str.strip()
    bins = [0, 18, 25, 35, 50, 120]
    labels = ['0-18', '19-25', '26-35', '36-50', '51+']
    dim_usuarios['faixa_etaria'] = pd.cut(dim_usuarios['idade'], bins=bins, labels=labels, right=False)

    # Transformando a dimensão de Livros
    print("  - Criando dim_livros...")
    dim_livros = df_books[['isbn', 'titulo', 'autor', 'ano_publicacao', 'editora']].copy()
    dim_livros['ano_publicacao'] = pd.to_numeric(dim_livros['ano_publicacao'], errors='coerce').fillna(0).astype(int)
    dim_livros = dim_livros[dim_livros['ano_publicacao'] != 0]

    # Criando a tabela de Fatos
    print("  - Criando fato_avaliacoes...")
    fato_avaliacoes = df_ratings[['id_usuario', 'isbn_livro', 'avaliacao']].copy()
    
    print("✅ Dados transformados com sucesso!")
    return dim_usuarios, dim_livros, fato_avaliacoes

# --- 3. ETAPA DE CARREGAMENTO (LOAD) ---
def carregar_para_duckdb(dim_usuarios, dim_livros, fato_avaliacoes):
    """Carrega os DataFrames transformados para um arquivo DuckDB."""
    print(f"\nIniciando carregamento para o Data Warehouse local ({ARQUIVO_DW})...")
    
    # Conecta ao arquivo DuckDB (ele será criado se não existir)
    con = duckdb.connect(database=ARQUIVO_DW, read_only=False)
    
    # Usa o DuckDB para registrar os dataframes como tabelas e salvá-los
    con.register('dim_usuarios_df', dim_usuarios)
    con.execute('CREATE OR REPLACE TABLE dim_usuarios AS SELECT * FROM dim_usuarios_df')
    
    con.register('dim_livros_df', dim_livros)
    con.execute('CREATE OR REPLACE TABLE dim_livros AS SELECT * FROM dim_livros_df')
    
    con.register('fato_avaliacoes_df', fato_avaliacoes)
    con.execute('CREATE OR REPLACE TABLE fato_avaliacoes AS SELECT * FROM fato_avaliacoes_df')
    
    con.close()
    print(f"✅ Dados carregados com sucesso no arquivo {ARQUIVO_DW}!")

# --- Orquestrador Principal ---
if __name__ == "__main__":
    print("--- INICIANDO PROCESSO DE ETL PARA O DATA WAREHOUSE (DUCKDB) ---")
    start_time = time.time()
    
    df_users, df_books, df_ratings = extrair_dados_do_postgres()
    
    if df_users is not None:
        dim_usuarios, dim_livros, fato_avaliacoes = transformar_dados(df_users, df_books, df_ratings)
        carregar_para_duckdb(dim_usuarios, dim_livros, fato_avaliacoes)
        
        end_time = time.time()
        print(f"\n--- PROCESSO DE ETL CONCLUÍDO EM {end_time - start_time:.2f} SEGUNDOS ---")