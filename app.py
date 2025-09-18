from flask import Flask, request, jsonify, render_template
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import difflib
import numpy as np

app = Flask(__name__)

scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("credenciais.json", scope)
client = gspread.authorize(creds)
sheet = client.open("Leaderboard").sheet1

QUESTOES = [
    {
        "id": 1,
        "pergunta": "mean(c(1,2,3,4,5))",
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
        "pergunta": "max(c(9,15,3,22,7))",
        "esperado": 22,
        "solucoes": [
            "max([9,15,3,22,7])",
            "np.max([9,15,3,22,7])"
        ]
    },
    {
        "id": 5,
        "pergunta": "min(c(9,15,3,22,7))",
        "esperado": 3,
        "solucoes": [
            "min([9,15,3,22,7])",
            "np.min([9,15,3,22,7])"
        ]
    },
    {
        "id": 6,
        "pergunta": "df <- data.frame(x=c(1,2,3), y=c(4,5,6))\nmean(df$y)",
        "esperado": 5.0,
        "solucoes": [
            'import pandas as pd\ndf = pd.DataFrame({"x":[1,2,3], "y":[4,5,6]})\ndf["y"].mean()'
        ]
    },
    {
        "id": 7,
        "pergunta": "df <- data.frame(x=c(1,2,3))\ndf2 <- df %>% mutate(y = x*2)",
        "esperado": [2,4,6], 
        "solucoes": [
            'import pandas as pd\ndf = pd.DataFrame({"x":[1,2,3]})\ndf["y"] = df["x"]*2\ndf["y"].tolist()'
        ]
    },
    {
        "id": 8,
        "pergunta": "df <- data.frame(grupo=c(\"A\",\"A\",\"B\",\"B\"), valor=c(1,2,3,4))\ndf %>% group_by(grupo) %>% summarize(media=mean(valor))",
        "esperado": {"A":1.5, "B":3.5},
        "solucoes": [
            'import pandas as pd\ndf = pd.DataFrame({"grupo":["A","A","B","B"], "valor":[1,2,3,4]})\ndf.groupby("grupo")["valor"].mean().to_dict()'
        ]
    },
    {
        "id": 9,
        "pergunta": "df <- data.frame(x=c(1,2,3), y=c(4,5,6))\nplot(df$x, df$y, type=\"l\")",
        "esperado": "grafico_linha",
        "solucoes": [
            'import pandas as pd\nimport matplotlib.pyplot as plt\ndf = pd.DataFrame({"x":[1,2,3], "y":[4,5,6]})\nplt.plot(df["x"], df["y"])\nplt.show()'
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


# --- Rotas ---
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

@app.route("/finalizar", methods=["POST"])
def finalizar():
    content = request.json
    nome = content.get("nome")
    pontos = content.get("pontos") 

    if not nome or pontos is None:
        return jsonify({"status": "erro", "message": "Dados inválidos"})

    sheet.append_row([nome, pontos])
    return jsonify({"status": "ok", "message": f"Pontuação final enviada: {pontos} pontos"})


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

        if valor == questao["esperado"]:
            sheet.append_row([nome, 10])
            return jsonify({"status": "ok", "message": "Correto! +10 pontos"})
        else:
            score = max(difflib.SequenceMatcher(None, codigo, s).ratio() for s in questao["solucoes"])
            if score > 0.6:
                return jsonify({"status": "quase", "message": "Quase lá, sua solução está próxima!"})
            return jsonify({"status": "erro", "message": "Resposta incorreta"})
    except Exception as e:
        return jsonify({"status": "erro", "message": str(e)})

if __name__ == "__main__":
    app.run(debug=True)