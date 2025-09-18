from flask import Flask, request, jsonify, render_template
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import difflib
import numpy as np
import os, json

app = Flask(__name__)

scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
cred_data = json.loads(os.environ["GOOGLE_CREDENTIALS"])
creds = ServiceAccountCredentials.from_json_keyfile_dict(cred_data, scope)
client = gspread.authorize(creds)
sheet = client.open("Leaderboard").sheet1

# ---------------- Função para atualizar pontuação acumulada ----------------
def atualizar_pontuacao(nome, pontos):
    data = sheet.get_all_records()
    df = pd.DataFrame(data)

    if not df.empty and "nome" in df.columns and nome in df["nome"].values:
        idx = df[df["nome"] == nome].index[0] + 2  # +2 porque gspread começa em 1 e tem header
        old = df.loc[df["nome"] == nome, "pontos"].values[0]
        sheet.update_cell(idx, 2, old + pontos)
    else:
        sheet.append_row([nome, pontos])

# ---------------- Questões ----------------
QUESTOES = [
    {
        "id": 1,
        "pergunta": "mean(c(1,2,3,4,5)) ➝ Traduza para Python",
        "esperado": 3.0,
        "solucoes": [
            "np.mean([1,2,3,4,5])",
            "sum([1,2,3,4,5])/5"
        ]
    },
    {
        "id": 2,
        "pergunta": "sum(c(10,20,30,40))",
        "esperado": 100,
        "solucoes": [
            "np.sum([10,20,30,40])",
            "sum([10,20,30,40])"
        ]
    },
    {
        "id": 3,
        "pergunta": "length(c(2,4,6,8,10,12))",
        "esperado": 6,
        "solucoes": [
            "len([2,4,6,8,10,12])"
        ]
    },
    {
        "id": 4,
        "pergunta": "df <- data.frame(x=c(1,2,3))\ndf2 <- df %>% mutate(y = x*2)",
        "esperado": [2,4,6], 
        "solucoes": [
            'import pandas as pd\ndf = pd.DataFrame({"x":[1,2,3]})\ndf["y"] = df["x"]*2\ndf["y"].tolist()'
        ]
    },
    {
        "id": 5,
        "pergunta": "Em Python, como você removeria valores nulos (NaN) de uma coluna chamada 'idade' em um DataFrame df?",
        "esperado": "dropna",
        "solucoes": [
            'df["idade"].dropna()',
            'df.dropna(subset=["idade"])'
        ]
    },
    {
        "id": 6,
        "pergunta": "Você tem um DataFrame com uma coluna 'nome' com espaços extras (ex: ' Ana '). Como limpar esses espaços?",
        "esperado": ["Ana"],
        "solucoes": [
            'df["nome"].str.strip()'
        ]
    },
    {
        "id": 7,
        "pergunta": "Crie um gráfico de dispersão em Python usando matplotlib com df['x'] e df['y']",
        "esperado": "grafico_dispersao",
        "solucoes": [
            'import matplotlib.pyplot as plt\nplt.scatter(df["x"], df["y"])\nplt.show()'
        ]
    },
    {
        "id": 8,
        "pergunta": "R: df <- data.frame(idade=c(20,25,30))\nnames(df)[names(df)=='idade'] <- 'anos'\nComo ficaria em Python?",
        "esperado": "anos",
        "solucoes": [
            'df.rename(columns={"idade":"anos"})'
    ]
    },
    {
        "id": 9,
        "pergunta": "Como criar uma nova coluna 'dobro' que seja o dobro da coluna 'x'?",
        "esperado": [2,4,6],
        "solucoes": [
            'df["dobro"] = df["x"]*2'
        ]
    },
    {
        "id": 10,
        "pergunta": "library(ggplot2)\ndf <- data.frame(x=c(1,2,3), y=c(4,5,6))\nggplot(df, aes(x=x, y=y)) + geom_point()",
        "esperado": "grafico_dispersao",
        "solucoes": [
            'import pandas as pd\nimport matplotlib.pyplot as plt\ndf = pd.DataFrame({"x":[1,2,3], "y":[4,5,6]})\nplt.scatter(df["x"], df["y"])\nplt.show()'
        ]
    }
]

# ---------------- Rotas ----------------
@app.route("/quiz", methods=["GET"])
def get_quiz():
    return jsonify(QUESTOES)

@app.route("/play")
def play():
    return render_template("index.html")

@app.route("/leaderboard", methods=["GET"])
def leaderboard():
    data = sheet.get_all_records()
    df = pd.DataFrame(data)
    if df.empty:
        return jsonify([])
    df = df.groupby("nome", as_index=False)["pontos"].sum()
    df = df.sort_values("pontos", ascending=False)
    return df.to_dict(orient="records")

@app.route("/submit", methods=["POST"])
def submit():
    content = request.json
    nome = content.get("nome")
    codigo = content.get("codigo")
    questao_id = content.get("questao_id")

    questao = next((q for q in QUESTOES if q["id"] == questao_id), None)
    if not questao:
        return jsonify({"status": "erro", "message": "Questão inválida"})

    local_vars = {}
    try:
        exec(codigo, {}, local_vars)

        valor = local_vars.get("result")

        if valor is None:
            if "__builtins__" in local_vars:
                del local_vars["__builtins__"]
            if local_vars:
                valor = list(local_vars.values())[-1]

        # Correto
        if valor == questao["esperado"]:
            atualizar_pontuacao(nome, 10)
            return jsonify({"status": "ok", "message": "Correto! +10 pontos"})
        else:
            # Verifica proximidade
            score = max(difflib.SequenceMatcher(None, codigo, s).ratio() for s in questao["solucoes"])
            if score > 0.6:
                atualizar_pontuacao(nome, 5)
                return jsonify({"status": "quase", "message": "Quase lá, sua solução está próxima! +5 pontos"})
            return jsonify({"status": "erro", "message": "Resposta incorreta"})
    except Exception as e:
        return jsonify({"status": "erro", "message": str(e)})

if __name__ == "__main__":
    app.run()
