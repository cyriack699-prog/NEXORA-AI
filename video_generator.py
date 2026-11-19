import uuid
from pathlib import Path
from urllib.parse import urljoin, quote

import requests

API_URL = "https://lightricks-ltx-video-distilled.hf.space"
VIDEO_DIR = Path(__file__).parent / "static" / "videos"


def generer_video(prompt, duree=5, format_video="paysage"):
    prompt = str(prompt).strip()

    if not prompt or len(prompt) > 1000:
        return {"error": "La description doit contenir entre 1 et 1000 caractères."}

    if not isinstance(duree, int) or duree not in (2, 5, 8):
        return {"error": "Durées disponibles : 2, 5 ou 8 secondes."}

    if format_video not in ("paysage", "portrait"):
        return {"error": "Format vidéo invalide."}

    largeur, hauteur = (
        (704, 512) if format_video == "paysage"
        else (512, 704)
    )

    donnees = {
        "data": [
            prompt,
            "worst quality, inconsistent motion, blurry, jittery, distorted",
            None,
            None,
            hauteur,
            largeur,
            "text-to-video",
            duree,
            9,
            42,
            True,
            3.0,
            True
        ]
    }

    try:
        with requests.Session() as session:
            reponse = session.post(
                f"{API_URL}/gradio_api/run/text_to_video",
                json=donnees,
                timeout=(30, 900)
            )

            if not reponse.ok:
                return {
                    "error": f"Erreur API LTX ({reponse.status_code}) : {reponse.text[:500]}"
                }

            resultat = reponse.json()

            if resultat.get("error"):
                return {"error": f"Erreur LTX : {resultat['error']}"}

            sortie = resultat.get("data", [])

            if not sortie and "output" in resultat:
                sortie = [resultat["output"]]

            if isinstance(sortie, list) and sortie:
                sortie = sortie[0]

            if not isinstance(sortie, dict):
                return {"error": "Réponse vidéo LTX inattendue."}

            video_data = sortie.get("video")

            if not isinstance(video_data, dict):
                return {"error": "LTX n'a retourné aucun fichier vidéo."}

            url = video_data.get("url")
            chemin = video_data.get("path")

            if url:
                url = urljoin(API_URL + "/", url)
            elif chemin:
                url = (
                    f"{API_URL}/gradio_api/file="
                    f"{quote(chemin, safe='/')}"
                )
            else:
                return {"error": "Lien du fichier vidéo absent."}

            telechargement = session.get(url, timeout=(30, 300))
            telechargement.raise_for_status()

            if not telechargement.content:
                return {"error": "Le fichier vidéo téléchargé est vide."}

            VIDEO_DIR.mkdir(parents=True, exist_ok=True)

            nom = f"nexora_{uuid.uuid4().hex[:12]}.mp4"
            (VIDEO_DIR / nom).write_bytes(telechargement.content)

            return {
                "video": f"/static/videos/{nom}",
                "message": "Vidéo créée avec succès avec LTX !"
            }

    except requests.Timeout:
        return {"error": "LTX met trop de temps à répondre. Réessaie plus tard."}

    except requests.RequestException as erreur:
        return {"error": f"Erreur de communication avec LTX : {erreur}"}

    except Exception as erreur:
        return {"error": f"Erreur vidéo : {erreur}"}
