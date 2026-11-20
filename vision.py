import os
import base64
import requests
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

MODEL = "gemini-3.5-flash-lite"

def analyser_photo(image):
    if not image:
        return "Aucune image reçue."

    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        return "Configuration Gemini manquante : clé API non configurée."

    try:
        if image.startswith(b"\x89PNG"):
            mime = "image/png"
        elif image.startswith(b"RIFF") and image[8:12] == b"WEBP":
            mime = "image/webp"
        elif image.startswith(b"GIF8"):
            mime = "image/gif"
        else:
            mime = "image/jpeg"

        image_base64 = base64.b64encode(image).decode("utf-8")

        url = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"{MODEL}:generateContent"
        )

        reponse = requests.post(
            url,
            headers={
                "x-goog-api-key": api_key,
                "Content-Type": "application/json"
            },
            json={
                "contents": [{
                    "parts": [
                        {
                            "inlineData": {
                                "mimeType": mime,
                                "data": image_base64
                            }
                        },
                        {
                            "text": (
                                "Analyse cette image en français. "
                                "Décris ce que tu vois. "
                                "Si elle contient un exercice scolaire, "
                                "lis l'énoncé et explique la résolution "
                                "étape par étape. Si elle contient du texte, "
                                "retranscris-le fidèlement."
                            )
                        }
                    ]
                }],
                "generationConfig": {
                    "maxOutputTokens": 1500,
                    "temperature": 0.4
                }
            },
            timeout=120
        )

        if not reponse.ok:
            try:
                detail = reponse.json().get("error", {}).get("message", "")
            except Exception:
                detail = ""

            return f"Gemini HTTP {reponse.status_code} : {detail or 'Erreur API'}"

        donnees = reponse.json()
        candidats = donnees.get("candidates", [])

        if not candidats:
            return "Gemini n'a fourni aucune réponse."

        parties = candidats[0].get("content", {}).get("parts", [])
        texte = "\n".join(
            p["text"] for p in parties if p.get("text")
        )

        return texte or "Aucune réponse textuelle reçue de Gemini."

    except requests.exceptions.Timeout:
        return "Délai dépassé : Gemini met trop de temps."
    except requests.exceptions.ConnectionError:
        return "Connexion impossible à Gemini."
    except Exception as e:
        return "Erreur technique : " + str(e)[:200]
