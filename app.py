import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd

scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("credenciais.json", scope)
client = gspread.authorize(creds)

# Abre a planilha e a aba
sheet = client.open("Leaderboard").sheet1

def add_score(nome, pontos):
    sheet.append_row([nome, pontos])

def get_leaderboard():
    data = sheet.get_all_records()
    df = pd.DataFrame(data)
    if not df.empty:
        df = df.groupby("Nome", as_index=False)["Pontos"].sum()
        df = df.sort_values("Pontos", ascending=False)
    return df

# --- APP ---
st.title("Quiz: R ➝ Python")

codigo_r = "mean(c(1,2,3,4,5))"
st.code(codigo_r, language="r")

nome = st.text_input("Seu nome:")
codigo_py = st.text_area("Traduza para Python:")

if st.button("Enviar"):
    try:
        local_vars = {}
        exec(codigo_py, {}, local_vars)
        if "result" in local_vars and local_vars["result"] == 3.0:
            st.success("Correto! +10 pontos")
            add_score(nome, 10)
        else:
            st.error("Resposta incorreta. Defina `result` com o valor certo.")
    except Exception as e:
        st.error(f"Erro no código: {e}")

st.subheader("🏆 Leaderboard")
df = get_leaderboard()
st.dataframe(df)
