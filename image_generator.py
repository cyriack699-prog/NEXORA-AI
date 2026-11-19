import os
import uuid
import base64
import requests
from dotenv import load_dotenv

load_dotenv()

def generer_image(prompt):
    account = os.getenv("CLOUDFLARE_ACCOUNT_ID")
    token = os.getenv("CLOUDFLARE_API_TOKEN")

    if not account or not token:
        return "Erreur image : configuration Cloudflare manquante."

    if not isinstance(prompt, str) or not prompt.strip():
        return "Erreur image : décris l'image souhaitée."

    url = (
        f"https://api.cloudflare.com/client/v4/accounts/{account}"
        "/ai/run/@cf/black-forest-labs/flux-1-schnell"
    )

    try:
        r = requests.post(
            url,
            headers={"Authorization": f"Bearer {token}"},
            json={"prompt": prompt.strip()},
            timeout=180
        )
        r.raise_for_status()

        donnees = r.json()
        image_base64 = donnees.get("result", {}).get("image")

        if not image_base64:
            return "Erreur image : aucune image reçue."

        contenu = base64.b64decode(image_base64)

        if contenu.startswith(b"\x89PNG\r\n\x1a\n"):
            extension = "png"
        elif contenu.startswith(b"\xff\xd8\xff"):
            extension = "jpg"
        else:
            return "Erreur image : format reçu non reconnu."

        os.makedirs("static/images", exist_ok=True)

        nom = str(uuid.uuid4()) + "." + extension
        chemin = os.path.join("static", "images", nom)

        with open(chemin, "wb") as fichier:
            fichier.write(contenu)

        return "/" + chemin

    except requests.exceptions.Timeout:
        return "Erreur image : délai dépassé."
    except requests.exceptions.HTTPError as e:
        try:
            donnees_erreur = e.response.json()
            erreurs = donnees_erreur.get("errors", [])
            codes = [
                str(erreur.get("code", ""))
                for erreur in erreurs
                if isinstance(erreur, dict)
            ]

            if "8007" in codes:
                return (
                    "Génération refusée par le filtre de sécurité "
                    "de Cloudflare. Essaie une description différente."
                )
        except (ValueError, AttributeError):
            pass

        return f"Erreur Cloudflare HTTP : {e.response.status_code}"
    except requests.exceptions.RequestException as e:
        return f"Erreur réseau : {type(e).__name__} - {str(e)[:300]}"
    except Exception:
        return "Erreur image : problème inattendu."
