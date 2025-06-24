import pandas as pd
import psycopg2
from psycopg2.extras import execute_values
import numpy as np
import time

def popular_banco():
    """
    Script completo para conectar, ler, limpar e popular o banco de dados
    Book-Crossing a partir dos arquivos CSV.
    """
    start_time = time.time()

    # --- 1. Conexão com o Banco de Dados ---
    print("Iniciando conexão com o banco de dados PostgreSQL...")
    try:
        conn = psycopg2.connect(
            host="localhost",
            port="5432",
            dbname="book_crossing_db",
            user="user",
            password="password"
        )
        cur = conn.cursor()
        print("✅ Conexão bem-sucedida!")
    except Exception as e:
        print(f"❌ Erro na conexão com o banco: {e}")
        return # Encerra o script se não puder conectar

    # --- 2. Leitura dos Arquivos CSV ---
    print("\nLendo arquivos CSV...")
    try:
        # Usando barras normais (/) para compatibilidade entre sistemas
        df_users = pd.read_csv('Book reviews/BX-Users.csv', sep=';', on_bad_lines='skip', encoding='latin-1')
        df_books = pd.read_csv('Book reviews/BX_Books.csv', sep=';', on_bad_lines='skip', encoding='latin-1', low_memory=False)
        df_ratings = pd.read_csv('Book reviews/BX-Book-Ratings.csv', sep=';', on_bad_lines='skip', encoding='latin-1')
        print("✅ Arquivos CSV lidos com sucesso!")
    except FileNotFoundError as e:
        print(f"❌ Erro: Arquivo não encontrado. Verifique os nomes e o caminho da pasta 'Book reviews'. {e}")
        cur.close()
        conn.close()
        return

    # --- 3. Limpeza e Preparação dos Dados ---
    print("\nLimpando e preparando os dados...")
    
    # Limpeza de Usuários
    df_users.rename(columns={'User-ID': 'id_usuario', 'Location': 'localizacao', 'Age': 'idade'}, inplace=True)
    df_users['idade'] = pd.to_numeric(df_users['idade'], errors='coerce')
    df_users['idade'] = df_users['idade'].apply(lambda x: x if pd.notnull(x) and 1 <= x <= 120 else None)

    # Limpeza de Livros
    df_books.rename(columns={'ISBN': 'isbn', 'Book-Title': 'titulo', 'Book-Author': 'autor', 
                             'Year-Of-Publication': 'ano_publicacao', 'Publisher': 'editora'}, inplace=True)
    df_books['ano_publicacao'] = pd.to_numeric(df_books['ano_publicacao'], errors='coerce').fillna(0).astype(int)
    # Remove ISBNs inválidos que não podem ser chave primária
    df_books.dropna(subset=['isbn'], inplace=True)
    df_books = df_books[df_books['isbn'].str.len() <= 13]

    # Limpeza de Avaliações e garantia de integridade
    df_ratings.rename(columns={'User-ID': 'id_usuario', 'ISBN': 'isbn_livro', 'Book-Rating': 'avaliacao'}, inplace=True)
    valid_users = set(df_users['id_usuario'])
    valid_isbns = set(df_books['isbn'])
    df_ratings = df_ratings[df_ratings['id_usuario'].isin(valid_users) & df_ratings['isbn_livro'].isin(valid_isbns)]
    print("✅ Dados limpos e prontos para inserção.")

    # --- 4. Inserção em Lote no Banco de Dados ---
    
    # Inserindo Usuários
    print("\nIniciando inserção de Usuários...")
    usuarios_para_inserir = list(df_users[['id_usuario', 'localizacao', 'idade']].itertuples(index=False, name=None))
    query_users = "INSERT INTO Usuarios (id_usuario, localizacao, idade) VALUES %s ON CONFLICT (id_usuario) DO NOTHING"
    execute_values(cur, query_users, usuarios_para_inserir, page_size=1000)
    print(f"✅ {len(usuarios_para_inserir)} usuários processados.")

    # Inserindo Livros
    print("Iniciando inserção de Livros...")
    livros_para_inserir = list(df_books[['isbn', 'titulo', 'autor', 'ano_publicacao', 'editora']].itertuples(index=False, name=None))
    query_books = "INSERT INTO Livros (isbn, titulo, autor, ano_publicacao, editora) VALUES %s ON CONFLICT (isbn) DO NOTHING"
    execute_values(cur, query_books, livros_para_inserir, page_size=1000)
    print(f"✅ {len(livros_para_inserir)} livros processados.")

    # Inserindo Avaliações
    print("Iniciando inserção de Avaliações...")
    avaliacoes_para_inserir = list(df_ratings.itertuples(index=False, name=None))
    query_ratings = "INSERT INTO Avaliacoes (id_usuario, isbn_livro, avaliacao) VALUES %s"
    execute_values(cur, query_ratings, avaliacoes_para_inserir, page_size=1000)
    print(f"✅ {len(avaliacoes_para_inserir)} avaliações processadas.")

    # --- 5. Finalização ---
    print("\nSalvando alterações no banco (commit)...")
    conn.commit()
    cur.close()
    conn.close()
    
    end_time = time.time()
    total_time = end_time - start_time
    print(f"🚀 Script finalizado com sucesso em {total_time:.2f} segundos!")

# Executa a função principal
if __name__ == "__main__":
    popular_banco()