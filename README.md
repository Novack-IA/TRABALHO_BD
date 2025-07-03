# Projeto Leitor Conectado: Sistema de Banco de Dados para Recomendações

Este é um projeto acadêmico desenvolvido para a disciplina de Banco de Dados, com o objetivo de projetar e implementar uma arquitetura de dados completa, envolvendo múltiplos tipos de bancos de dados para atender a diferentes casos de uso em um sistema de recomendação de livros.

A aplicação, "Leitor Conectado", utiliza o dataset público **Book-Crossing** e permite que usuários se cadastrem, façam login, busquem livros de diversas formas (incluindo uma busca por similaridade semântica baseada em vetores) e registrem suas avaliações.

O projeto culmina na construção de um Data Warehouse e uma análise de Business Intelligence (BI) sobre os dados de avaliações.

## Arquitetura da Solução

O fluxo de dados do projeto segue a seguinte arquitetura:

[Fonte: CSVs] -> [Script: popular_dataset.py] -> [Banco OLTP: PostgreSQL + pgvector]
|
V
[Script: enriquecer_usuarios.py] -> [Altera dados no PostgreSQL] <- [Script: gerar_vetores_otimizado.py]
|
V
[Aplicação Web: app.py (Streamlit)]
(Lê, escreve e atualiza no PostgreSQL)
|
V
[Script ETL: etl_dw.py] -> [Extrai do PG] -> [Data Warehouse OLAP: Arquivo DuckDB] -> [Ferramenta de BI]


## Tecnologias Utilizadas

* **Containerização:** Docker e Docker Compose
* **Banco de Dados Transacional/Vetorial (OLTP):** PostgreSQL com a extensão `pgvector`
* **Data Warehouse (OLAP):** DuckDB
* **Linguagem Principal:** Python 3.9+
* **Bibliotecas Python:**
    * `streamlit` para a interface web interativa
    * `pandas` para manipulação de dados
    * `psycopg2-binary` para a conexão com o PostgreSQL
    * `sentence-transformers` para a geração de embeddings (vetores)
    * `bcrypt` para hashing seguro de senhas
    * `Faker` para geração de dados sintéticos
    * `tqdm` para barras de progresso
    * `duckdb` para manipulação do Data Warehouse
* **Ferramenta de BI:** Power BI (ou outra ferramenta capaz de ler arquivos DuckDB/CSV)

## Estrutura do Projeto

/
|-- Book reviews/                  # Pasta para os arquivos CSV originais
|   |-- BX-Users.csv
|   |-- BX_Books.csv
|   -- BX-Book-Ratings.csv |-- data_warehouse_output/         # Pasta onde o DW é salvo |   -- book_crossing_dw.duckdb    # O arquivo do Data Warehouse
|-- app.py                         # A aplicação web Streamlit
|-- popular_dataset.py             # Script para carga inicial dos dados
|-- enriquecer_usuarios.py         # Script para gerar nomes, emails e senhas
|-- gerar_vetores_otimizado.py     # Script para gerar os embeddings vetoriais
|-- etl_dw.py                      # Script para criar o Data Warehouse com DuckDB
|-- schema.sql                     # Documentação da estrutura do banco PostgreSQL
|-- docker-compose.yml             # Define o serviço do PostgreSQL
|-- requirements.txt               # Lista de dependências Python
`-- README.md                      # Este arquivo


## Setup e Instalação

Siga os passos abaixo para configurar e executar o projeto.

**1. Pré-requisitos:**
* [Git](https://git-scm.com/downloads)
* [Docker](https://docs.docker.com/engine/install/) e [Docker Compose](https://docs.docker.com/compose/install/)
* [Python 3.9](https://www.python.org/downloads/) ou superior

**2. Clone o Repositório:**
```bash
git clone [URL-DO-SEU-REPOSITORIO]
cd [NOME-DO-SEU-REPOSITORIO]
3. Estrutura de Arquivos:

Crie uma pasta chamada Book reviews na raiz do projeto.

Coloque os três arquivos (BX-Users.csv, BX_Books.csv, BX-Book-Ratings.csv) dentro desta pasta.

4. Ambiente Virtual e Dependências:

É recomendado criar um ambiente virtual:

Bash

python -m venv venv
# No Windows:
.\venv\Scripts\activate
# No macOS/Linux:
source venv/bin/activate
Instale todas as dependências do Python a partir de um arquivo requirements.txt:

Bash

pip install -r requirements.txt
5. Iniciar o Banco de Dados:

Execute o Docker para iniciar o container do PostgreSQL em segundo plano:

Bash

docker-compose up -d
Modo de Uso (Ordem de Execução)
Execute os scripts na seguinte ordem para popular e preparar todo o ambiente.

1. Criar a Estrutura do Banco:

Conecte-se ao seu banco de dados (usando DBeaver, DataGrip ou a extensão do VS Code).

Copie e cole todo o conteúdo do arquivo schema.sql e execute-o. Isso criará as tabelas Usuarios, Livros e Avaliacoes com a estrutura final correta.

2. Carga Inicial dos Dados:

Execute o script para popular as tabelas com os dados dos arquivos CSV.

Bash

python popular_dataset.py
3. Enriquecimento dos Usuários:

Execute o script para gerar nome, email e senha para os usuários existentes. Este processo é longo.

Bash

python enriquecer_usuarios.py
4. Geração dos Vetores:

Execute o script para calcular os embeddings dos títulos dos livros. Este processo também é longo.

Bash

python gerar_vetores_otimizado.py
5. Construção do Data Warehouse:

Execute o script de ETL para criar o Data Warehouse local.

Bash

python etl_dw.py
Ao final, um arquivo book_crossing_dw.duckdb será criado na pasta data_warehouse_output.

6. Executar a Aplicação Web:

Com todos os dados prontos, inicie a aplicação Streamlit.

Bash

streamlit run app.py
Seu navegador abrirá com a interface de login. Use as credenciais de exemplo impressas no terminal ou crie um novo usuário.

7. Análise de BI:

Abra o Power BI.

Conecte-se à fonte de dados DuckDB (pode ser necessário um conector ODBC) ou modifique o etl_dw.py para salvar em CSV e importe os arquivos da pasta data_warehouse_output.

Crie as relações entre as tabelas e monte seu dashboard analítico.