import psycopg2
from psycopg2.extras import execute_values
from faker import Faker
import bcrypt
import time
import multiprocessing
import os
from tqdm import tqdm # Importa a biblioteca da barra de progresso

# --- Função "Trabalhadora" (continua a mesma) ---
def worker_hash_senha(dados_usuario):
    """
    Recebe os dados de um usuário (id, nome, email, senha em texto),
    gera o hash seguro para a senha e retorna os dados completos.
    """
    id_usuario, nome, email, senha_texto_puro = dados_usuario
    bytes_senha = senha_texto_puro.encode('utf-8')
    hash_senha = bcrypt.hashpw(bytes_senha, bcrypt.gensalt()).decode('utf-8')
    return (id_usuario, nome, email, hash_senha)

# --- Função Principal (com a barra de progresso) ---
def enriquecer_dados_paralelo():
    start_time = time.time()
    fake = Faker('pt_BR')
    
    print("Iniciando conexão com o banco de dados...")
    # (O bloco de conexão continua o mesmo)
    try:
        conn = psycopg2.connect(host="localhost", port="5432", dbname="book_crossing_db", user="user", password="password")
        cur = conn.cursor()
        print("✅ Conexão bem-sucedida!")
    except Exception as e:
        print(f"❌ Erro na conexão com o banco de dados: {e}")
        return

    print("Buscando usuários que precisam de enriquecimento...")
    # (A busca por usuários continua a mesma)
    cur.execute("SELECT id_usuario FROM Usuarios WHERE email IS NULL")
    usuarios_ids = cur.fetchall()
    total_users = len(usuarios_ids)
    
    if total_users == 0:
        print("✅ Nenhum usuário para atualizar.")
        cur.close()
        conn.close()
        return
        
    print(f"Encontrados {total_users} usuários para enriquecer.")

    # (A preparação de dados falsos continua a mesma)
    print("Preparando dados falsos (nomes e emails)...")
    dados_para_processar = []
    for user_tuple in usuarios_ids:
        id_usuario = user_tuple[0]
        nome = fake.name()
        email = f"user_{id_usuario}@example.com"
        senha_texto_puro = "senha123"
        dados_para_processar.append((id_usuario, nome, email, senha_texto_puro))
    print("✅ Dados para processamento preparados!")

    # --- MUDANÇA PRINCIPAL AQUI: PROCESSAMENTO PARALELO COM BARRA DE PROGRESSO ---
    num_cores = os.cpu_count()
    print(f"\nIniciando geração de hashes em paralelo (usando {num_cores} núcleos da CPU)...")
    
    dados_processados = []
    with multiprocessing.Pool(processes=num_cores) as pool:
        # Usamos pool.imap para processar os dados de forma "preguiçosa" (lazy),
        # o que permite que a barra de progresso seja atualizada assim que cada
        # tarefa termina, em vez de esperar por todas.
        # O tqdm envolve o pool.imap para criar a barra de progresso.
        with tqdm(total=total_users, desc="Gerando Hashes") as pbar:
            for resultado in pool.imap_unordered(worker_hash_senha, dados_para_processar):
                dados_processados.append(resultado)
                pbar.update(1) # Atualiza a barra a cada resultado recebido
    
    print("\n✅ Hashes gerados com sucesso!")

    # (O update em lote e a finalização continuam os mesmos)
    print("Iniciando atualização em massa no banco de dados...")
    update_query = """
        UPDATE Usuarios SET nome = data.nome, email = data.email, senha = data.senha
        FROM (VALUES %s) AS data(id, nome, email, senha)
        WHERE Usuarios.id_usuario = data.id;
    """
    execute_values(cur, update_query, dados_processados, page_size=2000)
    print("✅ Banco de dados atualizado!")

    print("\n--- Exemplos de Login para Teste (senha para todos: senha123) ---")
    for i in range(min(5, len(dados_processados))):
        print(f"Login: {dados_processados[i][2]}")

    print("\nSalvando alterações (commit)...")
    conn.commit()
    cur.close()
    conn.close()

    end_time = time.time()
    print(f"\n🚀 Script paralelo finalizado em {end_time - start_time:.2f} segundos!")

if __name__ == "__main__":
    enriquecer_dados_paralelo()