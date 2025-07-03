import pandas as pd
import psycopg2
import os
import time

# --- NOME DA PASTA ONDE O DATA WAREHOUSE SERÁ SALVO ---
PASTA_DW_OUTPUT = "data_warehouse_output"

# --- 1. ETAPA DE EXTRAÇÃO (EXTRACT) ---
def extrair_dados_do_postgres():
    """Conecta ao PostgreSQL e extrai as tabelas para DataFrames do Pandas."""
    print("Conectando ao PostgreSQL para extrair dados...")
    try:
        # Estabelece a conexão com o banco de dados local
        conn = psycopg2.connect(
            host="localhost", 
            port="5432", 
            dbname="book_crossing_db", 
            user="user", 
            password="password"
        )
        
        # Lê cada tabela para um DataFrame
        df_users = pd.read_sql("SELECT * FROM Usuarios", conn)
        df_books = pd.read_sql("SELECT * FROM Livros", conn)
        # Extrai apenas avaliações explícitas (nota de 1 a 10) para a análise
        df_ratings = pd.read_sql("SELECT * FROM Avaliacoes WHERE avaliacao > 0", conn)
        
        # Fecha a conexão com o banco
        conn.close()
        print("✅ Dados extraídos com sucesso do PostgreSQL!")
        return df_users, df_books, df_ratings
    except Exception as e:
        print(f"❌ Erro ao extrair dados do PostgreSQL: {e}")
        return None, None, None

# --- 2. ETAPA DE TRANSFORMAÇÃO (TRANSFORM) ---
def transformar_dados(df_users, df_books, df_ratings):
    """Transforma os dados brutos em um modelo de esquema estrela (star schema)."""
    print("\nIniciando transformação dos dados para o modelo estrela...")
    
    # Transformando a dimensão de Usuários
    print("  - Criando dim_usuarios...")
    dim_usuarios = df_users[['id_usuario', 'idade', 'localizacao']].copy()
    # Tenta extrair o país da coluna de localização
    dim_usuarios['pais'] = dim_usuarios['localizacao'].str.split(',').str[-1].str.strip()
    # Cria faixas etárias para facilitar a análise
    bins = [0, 18, 25, 35, 50, 120]
    labels = ['0-18', '19-25', '26-35', '36-50', '51+']
    dim_usuarios['faixa_etaria'] = pd.cut(dim_usuarios['idade'], bins=bins, labels=labels, right=False)

    # Transformando a dimensão de Livros
    print("  - Criando dim_livros...")
    dim_livros = df_books[['isbn', 'titulo', 'autor', 'ano_publicacao', 'editora']].copy()
    # Limpa anos de publicação inválidos (como 0) que podem ter sido carregados
    dim_livros['ano_publicacao'] = pd.to_numeric(dim_livros['ano_publicacao'], errors='coerce').fillna(0).astype(int)
    dim_livros = dim_livros[dim_livros['ano_publicacao'] > 0]

    # Criando a tabela de Fatos
    print("  - Criando fato_avaliacoes...")
    fato_avaliacoes = df_ratings[['id_usuario', 'isbn_livro', 'avaliacao']].copy()
    
    print("✅ Dados transformados com sucesso!")
    return dim_usuarios, dim_livros, fato_avaliacoes

# --- 3. ETAPA DE CARREGAMENTO (LOAD) ---
def salvar_csvs_para_bi(dim_usuarios, dim_livros, fato_avaliacoes):
    """Salva os DataFrames finais como arquivos CSV em uma pasta 'data_warehouse_output'."""
    print(f"\nIniciando salvamento dos arquivos CSV para o Data Warehouse...")
    
    # Cria o diretório para organizar os arquivos do DW, se ele não existir
    if not os.path.exists(PASTA_DW_OUTPUT):
        os.makedirs(PASTA_DW_OUTPUT)
    
    try:
        # Salva cada tabela de dimensão e de fatos como um arquivo CSV separado
        # index=False evita que o índice do DataFrame seja salvo como uma coluna no arquivo
        dim_usuarios.to_csv(f'{PASTA_DW_OUTPUT}/dim_usuarios.csv', index=False)
        print(f"  ✅ dim_usuarios.csv salvo com sucesso!")
        
        dim_livros.to_csv(f'{PASTA_DW_OUTPUT}/dim_livros.csv', index=False)
        print(f"  ✅ dim_livros.csv salvo com sucesso!")

        fato_avaliacoes.to_csv(f'{PASTA_DW_OUTPUT}/fato_avaliacoes.csv', index=False)
        print(f"  ✅ fato_avaliacoes.csv salvo com sucesso!")
        
        print(f"\nArquivos do DW salvos na pasta '{PASTA_DW_OUTPUT}'.")
        
    except Exception as e:
        print(f"❌ Erro ao salvar arquivos CSV: {e}")

# --- Orquestrador Principal do ETL ---
if __name__ == "__main__":
    print("--- INICIANDO PROCESSO DE ETL PARA O DATA WAREHOUSE ---")
    start_time = time.time()
    
    # Executa as três etapas em sequência
    df_users, df_books, df_ratings = extrair_dados_do_postgres()
    
    if df_users is not None:
        dim_usuarios, dim_livros, fato_avaliacoes = transformar_dados(df_users, df_books, df_ratings)
        salvar_csvs_para_bi(dim_usuarios, dim_livros, fato_avaliacoes)
        
        end_time = time.time()
        print(f"\n--- PROCESSO DE ETL CONCLUÍDO EM {end_time - start_time:.2f} SEGUNDOS ---")