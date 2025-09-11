# app.py (Final Feedback Test Version)
import streamlit as st
import os

# Tentativa de escrever em um arquivo de log direto
python_log_file_path = "./app/python_direct_log.txt"

# Garante que o diretório para o arquivo de log exista
log_directory = os.path.dirname(python_log_file_path) # Extrai o caminho do diretório (./app)
if log_directory and not os.path.exists(log_directory): # Verifica se o diretório não está vazio e não existe
    os.makedirs(log_directory) # Cria o diretório

# Agora, escreve no arquivo de log
try:
    with open(python_log_file_path, "a") as f: # Usando 'a' para append, para não sobrescrever a cada execução
        f.write("Python script execution started.\n")
except Exception as e:
    st.warning(f"Não foi possível escrever no arquivo de log: {e}")


print("FINAL FEEDBACK TEST: Python script execution started (via print).")
st.error("FINAL FEEDBACK TEST: Streamlit st.error() message from top of script.")

st.title("Final Feedback Test App")
st.write("This is a final attempt to get execution feedback.")

with open(python_log_file_path, "a") as f:
    f.write("FINAL FEEDBACK TEST: Streamlit UI elements (title, write) processed.\n")

print("FINAL FEEDBACK TEST: Streamlit UI elements processed (via print).")

# A simple function call
def test_func():
    with open(python_log_file_path, "a") as f:
        f.write("FINAL FEEDBACK TEST: In test_func.\n")
    print("FINAL FEEDBACK TEST: In test_func (via print).")
    st.write("Output from test_func.")

test_func()

with open(python_log_file_path, "a") as f:
    f.write("FINAL FEEDBACK TEST: Script execution finished.\n")

print("FINAL FEEDBACK TEST: Script execution finished (via print).")
