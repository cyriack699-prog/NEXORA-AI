import uuid
import json
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

    donnees = [
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

    try:
        with requests.Session() as session:
            # 1. Envoyer la demande dans la file d'attente Gradio
            reponse = session.post(
                f"{API_URL}/gradio_api/call/text_to_video",
                json={"data": donnees},
                timeout=(30, 60)
            )
            reponse.raise_for_status()

            evenement = reponse.json().get("event_id")

            if not evenement:
                return {"error": "LTX n'a pas fourni d'identifiant de génération."}

            # 2. Attendre le résultat de la génération
            flux = session.get(
                f"{API_URL}/gradio_api/call/text_to_video/{evenement}",
                stream=True,
                timeout=(30, 900)
            )
            flux.raise_for_status()

            resultat = None
            type_evenement = None

            for ligne in flux.iter_lines(decode_unicode=True):
                if not ligne:
                    continue

                ligne = ligne.strip()

                if ligne.startswith("event:"):
                    type_evenement = ligne[6:].strip()

                elif ligne.startswith("data:"):
                    contenu = ligne[5:].strip()

                    if contenu == "[DONE]":
                        break

                    try:
                        resultat = json.loads(contenu)
                    except json.JSONDecodeError:
                        continue

                    if type_evenement == "error":
                        return {"error": f"Erreur LTX : {resultat}"}

                    if type_evenement == "complete":
                        break

            flux.close()

            if resultat is None:
                return {"error": "LTX n'a retourné aucun résultat."}

            if isinstance(resultat, dict) and resultat.get("error"):
                return {"error": f"Erreur LTX : {resultat['error']}"}

            sortie = resultat.get("data", []) if isinstance(resultat, dict) else resultat

            if isinstance(sortie, list) and sortie:
                sortie = sortie[0]

            if not isinstance(sortie, dict):
                return {"error": "Format de réponse vidéo inattendu."}

            video_data = sortie.get("video", sortie)

            if not isinstance(video_data, dict):
                return {"error": "LTX n'a retourné aucun fichier vidéo."}

            url = video_data.get("url")
            chemin = video_data.get("path")

            if url:
                url = urljoin(API_URL + "/", url)
            elif chemin:
                url = f"{API_URL}/gradio_api/file={quote(chemin, safe='/')}"
            else:
                return {"error": "Lien du fichier vidéo absent."}

            # 3. Télécharger la vidéo
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
