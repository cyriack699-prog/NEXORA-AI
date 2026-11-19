import os
import uuid
import base64
import requests
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).parent / ".env")

MODEL = "@cf/black-forest-labs/flux-2-dev"

def generer_image(prompt):
    account = os.getenv("CLOUDFLARE_ACCOUNT_ID")
    token = os.getenv("CLOUDFLARE_API_TOKEN")

    if not account or not token:
        return "Erreur image : configuration Cloudflare manquante."

    if not isinstance(prompt, str) or not prompt.strip():
        return "Erreur image : décris l'image souhaitée."

    url = (
        f"https://api.cloudflare.com/client/v4/accounts/{account}"
        f"/ai/run/{MODEL}"
    )

    donnees = {
        "prompt": prompt.strip()[:3000],
        "steps": "25",
        "width": "1024",
        "height": "1024",
        "guidance": "4"
    }

    try:
        r = requests.post(
            url,
            headers={"Authorization": f"Bearer {token}"},
            data=donnees,
            timeout=300
        )

        if not r.ok:
            try:
                erreur = r.json()
                details = erreur.get("errors", [])
                return f"Erreur FLUX.2 HTTP {r.status_code} : {str(details)[:500]}"
            except ValueError:
                return f"Erreur FLUX.2 HTTP {r.status_code}."

        resultat = r.json()
        image_base64 = resultat.get("result", {}).get("image")

        if not image_base64:
            return "Erreur image : aucune image reçue de FLUX.2."

        contenu = base64.b64decode(image_base64)

        if contenu.startswith(b"\x89PNG\r\n\x1a\n"):
            extension = "png"
        elif contenu.startswith(b"\xff\xd8\xff"):
            extension = "jpg"
        else:
            return "Erreur image : format reçu non reconnu."

        dossier = Path(__file__).parent / "static" / "images"
        dossier.mkdir(parents=True, exist_ok=True)

        nom = str(uuid.uuid4()) + "." + extension
        chemin = dossier / nom
        chemin.write_bytes(contenu)

        return "/static/images/" + nom

    except requests.exceptions.Timeout:
        return "Erreur image : génération trop longue. Réessaie."
    except requests.exceptions.ConnectionError:
        return "Erreur image : connexion Cloudflare impossible."
    except requests.exceptions.RequestException:
        return "Erreur image : problème de communication avec Cloudflare."
    except Exception:
        return "Erreur image : problème inattendu."
