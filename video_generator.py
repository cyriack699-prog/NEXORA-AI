import time
import uuid
import json
from pathlib import Path

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
            False
        ]
    }

    try:
        session = requests.Session()
        creation = None
        derniere_erreur = None

        for tentative in range(3):
            try:
                creation = session.post(
                    f"{API_URL}/gradio_api/call/text_to_video",
                    json=donnees,
                    timeout=60
                )
                creation.raise_for_status()
                break
            except requests.RequestException as erreur:
                derniere_erreur = erreur
                if tentative < 2:
                    time.sleep(3)

        if creation is None:
            return {
                "error": f"Connexion LTX impossible après 3 tentatives : {derniere_erreur}"
            }

        event_id = creation.json().get("event_id")

        if not event_id:
            return {"error": "LTX n'a pas retourné d'identifiant de génération."}

        resultat = None
        url_evenement = f"{API_URL}/gradio_api/call/text_to_video/{event_id}"

        # Reconnexion au même événement : aucune nouvelle génération.
        for tentative in range(8):
            try:
                evenement = None

                with session.get(
                    url_evenement,
                    stream=True,
                    headers={"Accept": "text/event-stream"},
                    timeout=(30, 120)
                ) as response:
                    response.raise_for_status()

                    for ligne in response.iter_lines(decode_unicode=True):
                        if not ligne:
                            continue

                        if isinstance(ligne, bytes):
                            ligne = ligne.decode("utf-8", errors="replace")

                        if ligne.startswith("event:"):
                            evenement = ligne[6:].strip()

                        elif ligne.startswith("data:"):
                            contenu = ligne[5:].strip()

                            if evenement == "error":
                                return {"error": f"Erreur LTX : {contenu[:500]}"}

                            if evenement == "complete":
                                resultat = json.loads(contenu)
                                break

                if resultat is not None:
                    break

                if tentative < 7:
                    time.sleep(5)

            except requests.RequestException:
                if tentative == 7:
                    raise
                time.sleep(5)

        if resultat is None:
            return {
                "error": "La connexion avec LTX a été interrompue. Réessaie sans relancer immédiatement plusieurs générations."
            }

        if not isinstance(resultat, list) or not resultat:
            return {"error": "LTX n'a pas terminé correctement la génération."}

        video_data = resultat[0].get("video") if isinstance(resultat[0], dict) else None

        if not video_data:
            return {"error": "LTX n'a retourné aucun fichier vidéo."}

        url = video_data.get("url")

        if not url:
            return {"error": "Le lien de téléchargement de la vidéo est absent."}

        telechargement = None

        for tentative in range(3):
            try:
                telechargement = session.get(url, timeout=(30, 180))
                telechargement.raise_for_status()

                if not telechargement.content:
                    raise ValueError("Le fichier vidéo téléchargé est vide.")

                break

            except requests.RequestException:
                if tentative == 2:
                    raise
                time.sleep(3)

        VIDEO_DIR.mkdir(parents=True, exist_ok=True)

        nom = f"nexora_{uuid.uuid4().hex[:12]}.mp4"
        chemin = VIDEO_DIR / nom
        chemin.write_bytes(telechargement.content)

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
