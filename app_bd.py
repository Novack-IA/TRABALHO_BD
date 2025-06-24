import streamlit as st
import psycopg2
from sentence_transformers import SentenceTransformer
import pandas as pd
import bcrypt
import time

# --- 1. Configuração da Página e Funções de Cache ---

st.set_page_config(
    page_title="Leitor Conectado",
    layout="wide",
    initial_sidebar_state="collapsed"
)

@st.cache_resource
def carregar_modelo():
    """Carrega o modelo de IA SentenceTransformer uma única vez."""
    print("Carregando modelo de IA...")
    try:
        model = SentenceTransformer('all-MiniLM-L6-v2')
        print("Modelo carregado.")
        return model
    except Exception as e:
        st.error(f"Não foi possível baixar o modelo de IA. Verifique sua conexão. Erro: {e}")
        return None

@st.cache_resource
def iniciar_conexao_bd():
    """Inicia a conexão com o banco de dados PostgreSQL uma única vez."""
    print("Iniciando conexão com o BD...")
    try:
        conn = psycopg2.connect(
            host="localhost", port="5432", dbname="book_crossing_db", user="user", password="password"
        )
        print("Conexão bem-sucedida.")
        return conn
    except psycopg2.OperationalError as e:
        st.error(f"Erro de conexão com o PostgreSQL: {e}")
        st.warning("Verifique se o seu container Docker com o PostgreSQL está rodando (`docker-compose up -d`).")
        return None

conn = iniciar_conexao_bd()
modelo_ia = carregar_modelo()


# --- 2. Funções de Banco de Dados (Busca, Inserção, Update) ---

def buscar_livros(tipo_busca, termo_busca):
    """Função central que chama a rotina de busca apropriada."""
    if 'Título' in tipo_busca:
        return buscar_livros_por_similaridade(termo_busca)
    elif 'Autor' in tipo_busca:
        return buscar_livros_por_autor(termo_busca)
    elif 'Editora' in tipo_busca:
        return buscar_livros_por_editora(termo_busca)
    else: # ISBN
        return buscar_livro_por_isbn(termo_busca)

def buscar_livros_por_similaridade(termo_busca, top_n=15):
    if not conn or not modelo_ia: return pd.DataFrame()
    vetor_busca_str = str(modelo_ia.encode(termo_busca).tolist())
    query_sql = """
        SELECT
            l.isbn, l.titulo, l.autor, l.ano_publicacao, l.editora,
            l.embedding <-> %s as distancia,
            COALESCE(AVG(NULLIF(a.avaliacao, 0)), 0) AS media_avaliacao,
            COUNT(NULLIF(a.avaliacao, 0)) AS total_avaliacoes
        FROM Livros l
        LEFT JOIN Avaliacoes a ON l.isbn = a.isbn_livro
        WHERE l.embedding IS NOT NULL
        GROUP BY l.isbn, l.titulo, l.autor, l.ano_publicacao, l.editora, l.embedding
        ORDER BY distancia
        LIMIT 100;
    """
    try:
        df_candidatos = pd.read_sql_query(query_sql, conn, params=(vetor_busca_str,))
    except psycopg2.Error as e:
        st.error(f"Erro na busca por similaridade: {e}")
        return pd.DataFrame()

    if df_candidatos.empty: return pd.DataFrame()
    df_candidatos.sort_values(by=['distancia', 'ano_publicacao'], ascending=[True, False], inplace=True)
    df_filtrado = df_candidatos.groupby('titulo').head(2)
    return df_filtrado.sort_values(by='distancia').head(top_n)

def buscar_livros_por_autor(nome_autor, top_n=20):
    if not conn: return pd.DataFrame()
    query_sql = """
        SELECT
            l.isbn, l.titulo, l.autor, l.ano_publicacao, l.editora,
            COALESCE(AVG(NULLIF(a.avaliacao, 0)), 0) AS media_avaliacao,
            COUNT(NULLIF(a.avaliacao, 0)) AS total_avaliacoes
        FROM Livros l
        LEFT JOIN Avaliacoes a ON l.isbn = a.isbn_livro
        WHERE l.autor ILIKE %s
        GROUP BY l.isbn, l.titulo, l.autor, l.ano_publicacao, l.editora
        ORDER BY l.ano_publicacao DESC, total_avaliacoes DESC, media_avaliacao DESC;
    """
    df = pd.read_sql_query(query_sql, conn, params=(f'%{nome_autor}%',))
    if not df.empty:
        df_filtrado = df.sort_values(by='ano_publicacao', ascending=False).groupby('titulo').head(2)
        return df_filtrado.head(top_n)
    return pd.DataFrame()

def buscar_livros_por_editora(nome_editora, top_n=20):
    if not conn: return pd.DataFrame()
    query_sql = """
        SELECT
            l.isbn, l.titulo, l.autor, l.ano_publicacao, l.editora,
            COALESCE(AVG(NULLIF(a.avaliacao, 0)), 0) AS media_avaliacao,
            COUNT(NULLIF(a.avaliacao, 0)) AS total_avaliacoes
        FROM Livros l
        LEFT JOIN Avaliacoes a ON l.isbn = a.isbn_livro
        WHERE l.editora ILIKE %s
        GROUP BY l.isbn, l.titulo, l.autor, l.ano_publicacao, l.editora
        ORDER BY l.ano_publicacao DESC, total_avaliacoes DESC, media_avaliacao DESC;
    """
    df = pd.read_sql_query(query_sql, conn, params=(f'%{nome_editora}%',))
    if not df.empty:
        df_filtrado = df.sort_values(by='ano_publicacao', ascending=False).groupby('titulo').head(2)
        return df_filtrado.head(top_n)
    return pd.DataFrame()

def buscar_livro_por_isbn(isbn):
    if not conn: return pd.DataFrame()
    query_sql = """
        SELECT
            l.isbn, l.titulo, l.autor, l.ano_publicacao, l.editora,
            COALESCE(AVG(NULLIF(a.avaliacao, 0)), 0) AS media_avaliacao,
            COUNT(NULLIF(a.avaliacao, 0)) AS total_avaliacoes
        FROM Livros l
        LEFT JOIN Avaliacoes a ON l.isbn = a.isbn_livro
        WHERE l.isbn = %s
        GROUP BY l.isbn, l.titulo, l.autor, l.ano_publicacao, l.editora;
    """
    df = pd.read_sql_query(query_sql, conn, params=(isbn,))
    return df

def salvar_avaliacao(id_usuario, isbn, avaliacao):
    if not conn: return False, "Sem conexão com o banco."
    avaliacao = int(avaliacao)
    update_query = """
        INSERT INTO Avaliacoes (id_usuario, isbn_livro, avaliacao)
        VALUES (%s, %s, %s)
        ON CONFLICT (id_usuario, isbn_livro) DO UPDATE SET avaliacao = EXCLUDED.avaliacao;
    """
    try:
        with conn.cursor() as cur:
            cur.execute(update_query, (id_usuario, isbn, avaliacao))
            conn.commit()
        return True, "Avaliação registrada com sucesso!"
    except Exception as e:
        conn.rollback()
        return False, f"Erro ao salvar avaliação: {e}"

# --- 3. Gerenciamento de Estado da Sessão ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
    st.session_state['user_id'] = None
    st.session_state['user_name'] = ""
    st.session_state['page'] = 'Login'
if 'last_search_term' not in st.session_state:
    st.session_state['last_search_term'] = ""
if 'last_search_type' not in st.session_state:
    st.session_state['last_search_type'] = 'Similaridade de Título (Vetorial)'
if 'search_results_df' not in st.session_state:
    st.session_state['search_results_df'] = pd.DataFrame()

# --- 4. Definição das Páginas (UI) ---

def pagina_login_cadastro():
    st.header("Bem-vindo ao Leitor Conectado")
    choice = st.radio("Selecione uma opção:", ("Login", "Cadastro"), horizontal=True)

    if choice == "Login":
        # CHAVE DO FORMULÁRIO AQUI:
        with st.form(key="login_form"): # KEY VEM NO st.form()
            email = st.text_input("Email", key="login_email")
            senha = st.text_input("Senha", type="password", key="login_senha")
            # REMOVIDO key DO st.form_submit_button()
            submitted = st.form_submit_button("Entrar")
            if submitted:
                if conn and email and senha:
                    with conn.cursor() as cur:
                        cur.execute("SELECT id_usuario, nome, senha FROM Usuarios WHERE email = %s", (email,))
                        user_data = cur.fetchone()
                    if user_data and bcrypt.checkpw(senha.encode('utf-8'), user_data[2].encode('utf-8')):
                        st.session_state['logged_in'] = True
                        st.session_state['user_id'] = user_data[0]
                        st.session_state['user_name'] = user_data[1]
                        st.session_state['page'] = 'Busca'
                        st.rerun()
                    else:
                        st.error("Email ou senha inválidos.")
    elif choice == "Cadastro":
        # CHAVE DO FORMULÁRIO AQUI:
        with st.form(key="cadastro_form"): # KEY VEM NO st.form()
            st.subheader("Cadastro de Novo Usuário")
            nome = st.text_input("Nome Completo*", key="cadastro_nome")
            email = st.text_input("Email*", key="cadastro_email")
            senha = st.text_input("Senha*", type="password", key="cadastro_senha")
            cidade = st.text_input("Cidade", key="cadastro_cidade")
            estado = st.text_input("Estado", key="cadastro_estado")
            pais = st.text_input("País", key="cadastro_pais")
            # REMOVIDO key DO st.form_submit_button()
            submitted = st.form_submit_button("Cadastrar")
            if submitted:
                if not nome or not email or not senha:
                    st.warning("Nome, email e senha são obrigatórios.")
                else:
                    localizacao = f"{cidade}, {estado}, {pais}".strip(", ")
                    hash_senha = bcrypt.hashpw(senha.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                    try:
                        with conn.cursor() as cur:
                            cur.execute("INSERT INTO Usuarios (nome, email, senha, localizacao) VALUES (%s, %s, %s, %s)",
                                        (nome, email, hash_senha, localizacao))
                            conn.commit()
                        st.success("Usuário cadastrado com sucesso! Por favor, faça o login.")
                        st.balloons()
                        time.sleep(2)
                        st.rerun()
                    except psycopg2.errors.UniqueViolation:
                        conn.rollback()
                        st.error("Este email já está cadastrado.")
                    except psycopg2.errors.NotNullViolation as e:
                        conn.rollback()
                        st.error(f"Erro: ID de usuário não pode ser nulo. Verifique a configuração da tabela. Detalhes: {e}")
                        print(f"ERRO SQL: {e}")
                    except Exception as e:
                        conn.rollback()
                        st.error(f"Ocorreu um erro inesperado: {e}")
                        print(f"ERRO GERAL: {e}")

def pagina_principal_busca():
    st.sidebar.header(f"Bem-vindo(a), {st.session_state['user_name']}!")
    if st.sidebar.button("Sair", key="logout_btn"):
        for key in st.session_state.keys():
            del st.session_state[key]
        st.rerun()

    st.title("🔎 Encontre sua Próxima Leitura")

    termo_busca_input = st.text_input(
        "Busque por título, autor, editora ou ISBN:",
        value=st.session_state['last_search_term'],
        key="search_term_input"
    )
    tipo_busca_select = st.selectbox(
        "Selecione o tipo de busca:",
        ('Similaridade de Título (Vetorial)', 'Nome do Autor (Relacional)', 'Nome da Editora (Relacional)', 'ISBN (Busca Exata)'),
        index=('Similaridade de Título (Vetorial)', 'Nome do Autor (Relacional)', 'Nome da Editora (Relacional)', 'ISBN (Busca Exata)').index(st.session_state['last_search_type']),
        key="search_type_select"
    )

    if st.button("Buscar Livros", key="perform_search_btn"):
        if termo_busca_input and conn and modelo_ia:
            st.session_state['last_search_term'] = termo_busca_input
            st.session_state['last_search_type'] = tipo_busca_select
            st.markdown("---")
            with st.spinner("Buscando no banco de dados... Por favor, aguarde."):
                resultados_df_temp = buscar_livros(tipo_busca_select, termo_busca_input)
                st.session_state['search_results_df'] = resultados_df_temp
        else:
            st.warning("Por favor, digite um termo de busca.")

    if not st.session_state['search_results_df'].empty:
        st.subheader("Resultados da Busca:")
        for index, row in st.session_state['search_results_df'].iterrows():
            res_col1, res_col2 = st.columns([3, 1])
            with res_col1:
                st.markdown(f"**{row['titulo']}**")
                st.caption(f"Autor: {row['autor']}")
                ano = int(row['ano_publicacao']) if pd.notna(row['ano_publicacao']) and row['ano_publicacao'] > 0 else "Desconhecido"
                st.caption(f"Editora: {row['editora']} | Ano: {ano}")

                with st.expander("Avaliar este livro"):
                    # CHAVE DO FORMULÁRIO AQUI:
                    with st.form(key=f"avaliacao_form_{row['isbn']}", clear_on_submit=False):
                        rating_value = st.slider("Sua nota:", 1, 10, 5, key=f"rating_{row['isbn']}_slider")
                        # REMOVIDO key DO st.form_submit_button()
                        submit_avaliacao = st.form_submit_button("Salvar Avaliação")

                        if submit_avaliacao:
                            success, message = salvar_avaliacao(st.session_state['user_id'], row['isbn'], rating_value)
                            if success:
                                st.success(message)
                                st.session_state['search_results_df'] = buscar_livros(
                                    st.session_state['last_search_type'],
                                    st.session_state['last_search_term']
                                )
                            else:
                                st.error(message)
            with res_col2:
                if row['total_avaliacoes'] > 0:
                    st.metric(label="Avaliação Média", value=f"{row['media_avaliacao']:.2f} ⭐", delta=f"{int(row['total_avaliacoes'])} avaliações", delta_color="off")
                else:
                    st.metric(label="Avaliação Média", value="N/A", delta="Sem avaliações", delta_color="off")
            st.markdown("---")
    else:
        # Lógica para o botão inicial ou mensagem de nenhum resultado
        # Esta parte pode ser simplificada, pois o primeiro `st.button("Buscar Livros")`
        # já gerencia a busca e o state['search_results_df']
        pass # Removemos a duplicação do botão de busca aqui para simplificar a lógica de UI


# --- 5. Roteador Principal da Aplicação ---
if not conn or not modelo_ia:
    st.error("A aplicação não pôde ser inicializada. Verifique a conexão com o banco e a internet.")
elif st.session_state['logged_in']:
    pagina_principal_busca()
else:
    pagina_login_cadastro()