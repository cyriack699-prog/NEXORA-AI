from flask import Flask, render_template, request, jsonify
from cerveau import repondre

app = Flask(__name__)

@app.route("/")
def accueil():
    return render_template("index.html")

@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json() or {}
    message = data.get("message", "").strip()

    if not message:
        return jsonify({"response": "Écris un message !"})

    return jsonify({
        "response": repondre(message)
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
