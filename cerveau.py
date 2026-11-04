import os
import json
import urllib.request
import urllib.error

historique = []

def repondre(message):
    cle = os.environ.get("GROQ_API_KEY")

    if not cle:
        return "Clé API introuvable."

    historique.append({
        "role": "user",
        "content": message
    })

    donnees = {
        "model": "openai/gpt-oss-20b",        "messages": [
            {
                "role": "system",
                "content": "Tu es NEXORA AI, un assistant intelligent, amical et pédagogique. Tu réponds naturellement et tu gardes le contexte de la conversation."
            }
        ] + historique[-20:]
    }

    requete = urllib.request.Request(
        "https://api.groq.com/openai/v1/chat/completions",
        data=json.dumps(donnees).encode("utf-8"),
        headers={
            "Authorization": "Bearer " + cle,
            "Content-Type": "application/json",
            "User-Agent": "NEXORA-AI/1.0",
        },
        method="POST"
    )

    try:
        with urllib.request.urlopen(requete, timeout=60) as reponse:
            resultat = json.loads(reponse.read().decode("utf-8"))
            texte = resultat["choices"][0]["message"]["content"]

            historique.append({
                "role": "assistant",
                "content": texte
            })

            return texte

    except Exception as erreur:
        return "Erreur : " + str(erreur)
