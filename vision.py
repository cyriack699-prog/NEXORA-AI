import os
import base64
import requests
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

MODEL = "gemini-3.5-flash-lite"

def analyser_photo(image, question=None):
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
                                "Tu es le système de vision de NEXORA AI. "
                                "Analyse l'image avec précision et réponds dans un français naturel, "
                                "fluide, clair et professionnel.\n\n"
                                "RÈGLES DE RÉDACTION :\n"
                                "- Commence directement par l'information essentielle.\n"
                                "- Privilégie des paragraphes naturels et bien construits.\n"
                                "- N'utilise des titres ou des listes que s'ils améliorent réellement la clarté.\n"
                                "- Évite les répétitions, les longues introductions et les conclusions artificielles.\n"
                                "- Décris uniquement les éléments réellement visibles. Ne présente jamais une supposition comme un fait.\n"
                                "- Si un détail est incertain, indique-le clairement.\n"
                                "- Pour les textes présents dans l'image, recopie fidèlement les mots lisibles. "
                                "Ne corrige pas silencieusement les fautes et ne prétends pas voir un texte illisible.\n"
                                "- Adapte la longueur à la question : sois concis lorsque c'est suffisant et détaillé lorsque c'est utile.\n"
                                "- Réponds précisément à la demande, sans transformer systématiquement l'analyse en catalogue.\n\n"
                                "DEMANDE DE L'UTILISATEUR :\n"
                                + (question.strip() if isinstance(question, str) and question.strip()
                                   else "Décris cette image et explique ses éléments importants.")
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
