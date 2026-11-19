import os
import base64
import requests
from dotenv import load_dotenv

load_dotenv()

def analyser_photo(image):
    account = os.getenv("CLOUDFLARE_ACCOUNT_ID")
    token = os.getenv("CLOUDFLARE_API_TOKEN")

    if not account or not token:
        return "Configuration Cloudflare manquante."

    try:
        image_base64 = base64.b64encode(image).decode("utf-8")

        url = (
            f"https://api.cloudflare.com/client/v4/accounts/{account}"
            "/ai/run/@cf/meta/llama-3.2-11b-vision-instruct"
        )

        reponse = requests.post(
            url,
            headers={"Authorization": f"Bearer {token}"},
            json={
                "messages": [
                    {
                        "role": "user",
                        "content": "Lis cette photo et explique l'exercice étape par étape en français."
                    }
                ],
                "image": "data:image/jpeg;base64," + image_base64,
                "max_tokens": 1000
            },
            timeout=120
        )

        if not reponse.ok:
            try:
                erreur = reponse.json().get("errors", [])
                detail = "; ".join(
                    str(e.get("message", "")) for e in erreur
                )
            except Exception:
                detail = ""

            return f"Cloudflare HTTP {reponse.status_code} : {detail or 'Erreur API'}"

        donnees = reponse.json()
        resultat = donnees.get("result", {})

        return resultat.get(
            "response",
            "Aucune réponse reçue du modèle Vision."
        )

    except requests.exceptions.Timeout:
        return "Délai dépassé : Cloudflare met trop de temps."
    except requests.exceptions.ConnectionError:
        return "Connexion impossible à Cloudflare."
    except Exception as e:
        return "Erreur technique : " + str(e)[:200]
