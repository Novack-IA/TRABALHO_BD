import psycopg2
from psycopg2.extras import execute_values
from sentence_transformers import SentenceTransformer
import numpy as np
import time

def gerar_embeddings_otimizado():
    """
    Script OTIMIZADO para gerar embeddings em lote e salvá-los no banco.
    """
    start_time = time.time()
    
    # Define o tamanho do lote que será processado de cada vez
    BATCH_SIZE = 256

    # --- 1. Conexão e Carregamento do Modelo ---
    print("Iniciando conexão e carregamento do modelo...")
    try:
        conn = psycopg2.connect(host="localhost", port="5432", dbname="book_crossing_db", user="user", password="password")
        cur = conn.cursor()
        model = SentenceTransformer('all-MiniLM-L6-v2')
        print("✅ Conexão e modelo prontos!")
    except Exception as e:
        print(f"❌ Erro na inicialização: {e}")
        return

    # --- 2. Buscar Todos os Livros sem Embedding de Uma Vez ---
    print("\nBuscando todos os livros que ainda não possuem vetor...")
    cur.execute("SELECT isbn, titulo FROM Livros WHERE embedding IS NULL AND titulo IS NOT NULL")
    livros_para_processar = cur.fetchall()
    total_livros = len(livros_para_processar)
    print(f"Encontrados {total_livros} livros para processar.")

    # --- 3. Processamento em Lotes ---
    print(f"\nIniciando processamento em lotes de {BATCH_SIZE}...")
    # O loop avança de BATCH_SIZE em BATCH_SIZE
    for i in range(0, total_livros, BATCH_SIZE):
        # Pega a fatia (batch) atual de livros
        lote_livros = livros_para_processar[i : i + BATCH_SIZE]
        
        # Separa os isbns e os títulos do lote
        isbns_lote = [livro[0] for livro in lote_livros]
        titulos_lote = [livro[1] for livro in lote_livros]

        # Gera os embeddings para todo o lote de títulos de uma só vez
        embeddings_lote = model.encode(titulos_lote)

        # Prepara os dados para o update em lote
        dados_para_update = []
        for j in range(len(isbns_lote)):
            dados_para_update.append((isbns_lote[j], embeddings_lote[j].tolist()))

        # --- 4. Update em Lote no Banco de Dados ---
        # Este comando SQL atualiza múltiplas linhas de uma vez
        update_query = """
            UPDATE Livros SET embedding = data_table.embedding
            FROM (VALUES %s) AS data_table(isbn, embedding)
            WHERE Livros.isbn = data_table.isbn
        """
        execute_values(cur, update_query, dados_para_update)
        
        print(f"  Lote processado: {min(i + BATCH_SIZE, total_livros)}/{total_livros} livros atualizados.")

    # --- 5. Finalização ---
    print("\nSalvando alterações finais no banco (commit)...")
    conn.commit()
    cur.close()
    conn.close()

    end_time = time.time()
    total_time = end_time - start_time
    print(f"🚀 Script otimizado finalizado em {total_time:.2f} segundos!")

if __name__ == "__main__":
    gerar_embeddings_otimizado()