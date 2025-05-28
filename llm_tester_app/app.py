# app.py

import streamlit as st
import requests
import pandas as pd
import psycopg2
from urllib.parse import urlparse

# --- Configuração Inicial da Página e Variáveis ---

st.set_page_config(
    page_title="Comparador de LLMs",
    page_icon="🤖",
    layout="wide",
)

# Modelos gratuitos disponíveis no OpenRouter (verifique o site para a lista mais atual)
FREE_MODELS = [
    "mistralai/mistral-7b-instruct:free",
    "google/gemma-7b-it:free",
    "nousresearch/nous-hermes-2-mixtral-8x7b-dpo:free",
    "openchat/openchat-7b:free",
]

# --- Funções do Banco de Dados ---

# Conecta ao banco de dados usando as credenciais do Streamlit Secrets
@st.cache_resource
def get_db_connection():
    """Retorna uma conexão com o banco de dados PostgreSQL."""
    conn_str = st.secrets["DB_CONNECTION_STRING"]
    return psycopg2.connect(conn_str)

# Cria a tabela de resultados se ela não existir
def setup_database(conn):
    """Cria a tabela de avaliações no banco de dados, se não existir."""
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS llm_evaluations (
                id SERIAL PRIMARY KEY,
                prompt TEXT NOT NULL,
                model_name VARCHAR(255) NOT NULL,
                response TEXT NOT NULL,
                rating INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        conn.commit()

# --- Funções da API do OpenRouter ---

@st.cache_data(show_spinner="Consultando modelos...")
def query_openrouter_model(prompt, model_name):
    """Envia uma requisição para a API da OpenRouter e retorna a resposta."""
    try:
        response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {st.secrets['OPENROUTER_API_KEY']}",
                "Content-Type": "application/json"
            },
            json={
                "model": model_name,
                "messages": [{"role": "user", "content": prompt}]
            }
        )
        response.raise_for_status()  # Lança um erro para códigos de status ruins (4xx ou 5xx)
        data = response.json()
        return data['choices'][0]['message']['content']
    except requests.exceptions.RequestException as e:
        return f"Erro na API: {e}"
    except (KeyError, IndexError) as e:
        return f"Erro ao processar a resposta da API: {e}"

# --- Interface Principal do Streamlit ---

st.title("🧪 Comparador e Avaliador de Modelos LLM")
st.markdown("Use este app para enviar uma pergunta para diferentes LLMs, avaliar as respostas e salvar os resultados.")

# Inicializa o estado da sessão para armazenar os resultados temporariamente
if 'responses' not in st.session_state:
    st.session_state.responses = []
if 'prompt' not in st.session_state:
    st.session_state.prompt = ""

# Conecta e configura o banco de dados
try:
    conn = get_db_connection()
    setup_database(conn)
except Exception as e:
    st.error(f"Não foi possível conectar ao banco de dados: {e}")
    st.stop()

# Abas para separar as funcionalidades
tab1, tab2 = st.tabs(["Nova Avaliação", "Rever Resultados Salvos"])

# --- Aba 1: Nova Avaliação ---
with tab1:
    st.header("1. Faça sua Pergunta")

    selected_models = st.multiselect(
        "Selecione os modelos que deseja testar:",
        options=FREE_MODELS,
        default=FREE_MODELS
    )

    prompt_text = st.text_area("Digite sua pergunta ou comando aqui:", height=150, key="prompt_input")

    if st.button("Enviar Pergunta para os Modelos", type="primary"):
        if not prompt_text:
            st.warning("Por favor, digite uma pergunta.")
        elif not selected_models:
            st.warning("Por favor, selecione pelo menos um modelo.")
        else:
            st.session_state.prompt = prompt_text
            st.session_state.responses = []
            for model in selected_models:
                response = query_openrouter_model(prompt_text, model)
                st.session_state.responses.append({"model": model, "response": response})

    if st.session_state.responses:
        st.header("2. Avalie as Respostas")
        
        with st.form("evaluation_form"):
            ratings = {}
            for i, res in enumerate(st.session_state.responses):
                st.subheader(f"Modelo: `{res['model']}`")
                st.markdown(res['response'])
                ratings[i] = st.slider(
                    f"Nota para {res['model']}",
                    min_value=1,
                    max_value=5,
                    key=f"rating_{i}"
                )
                st.divider()

            submitted = st.form_submit_button("Salvar Avaliações no Banco de Dados")
            if submitted:
                try:
                    with conn.cursor() as cur:
                        for i, res in enumerate(st.session_state.responses):
                            cur.execute(
                                """
                                INSERT INTO llm_evaluations (prompt, model_name, response, rating)
                                VALUES (%s, %s, %s, %s)
                                """,
                                (st.session_state.prompt, res['model'], res['response'], ratings[i])
                            )
                        conn.commit()
                    st.success("Avaliações salvas com sucesso!")
                    # Limpa o estado para uma nova rodada
                    st.session_state.responses = []
                    st.session_state.prompt = ""
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro ao salvar no banco de dados: {e}")
                    conn.rollback()


# --- Aba 2: Rever Resultados ---
with tab2:
    st.header("Resultados Salvos Anteriormente")
    
    if st.button("Atualizar Resultados"):
        st.cache_data.clear() # Limpa o cache para buscar novos dados

    try:
        df = pd.read_sql("SELECT * FROM llm_evaluations ORDER BY created_at DESC", conn)
        if not df.empty:
            st.dataframe(df, use_container_width=True)
        else:
            st.info("Nenhuma avaliação foi salva ainda.")
    except Exception as e:
        st.error(f"Erro ao buscar os dados: {e}")
