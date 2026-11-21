import os
import uuid
import base64
import requests
from pathlib import Path
from urllib.parse import quote
from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).parent / ".env")

MODEL_POLLI = "tongyi-mai/z-image-turbo"
MODEL_CLOUDFLARE = "@cf/black-forest-labs/flux-2-dev"


def sauvegarder_image(contenu):
    if contenu.startswith(b"\x89PNG\r\n\x1a\n"):
        extension = "png"
    elif contenu.startswith(b"\xff\xd8\xff"):
        extension = "jpg"
    else:
        return None

    dossier = Path(__file__).parent / "static" / "images"
    dossier.mkdir(parents=True, exist_ok=True)

    nom = str(uuid.uuid4()) + "." + extension
    (dossier / nom).write_bytes(contenu)
    return "/static/images/" + nom


def generer_pollinations(prompt):
    cle = os.getenv("POLLINATIONS_API_KEY")
    if not cle:
        raise Exception("Clé Pollinations absente sur Render.")

    url = "https://gen.pollinations.ai/image/" + quote(prompt[:3000], safe="")

    r = requests.get(
        url,
        headers={"Authorization": f"Bearer {cle}"},
        params={
            "model": MODEL_POLLI,
            "width": 1024,
            "height": 1024
        },
        timeout=300
    )

    if not r.ok:
        raise Exception(f"Pollinations HTTP {r.status_code}: {r.text[:300]}")

    resultat = sauvegarder_image(r.content)
    if not resultat:
        raise Exception("Pollinations n'a pas renvoyé une image PNG ou JPEG.")

    return resultat


def generer_cloudflare(prompt):
    account = os.getenv("CLOUDFLARE_ACCOUNT_ID")
    token = os.getenv("CLOUDFLARE_API_TOKEN")

    if not account or not token:
        raise Exception("Configuration Cloudflare manquante.")

    url = (
        f"https://api.cloudflare.com/client/v4/accounts/{account}"
        f"/ai/run/{MODEL_CLOUDFLARE}"
    )

    r = requests.post(
        url,
        headers={"Authorization": f"Bearer {token}"},
        files={
            "prompt": (None, prompt[:3000]),
            "steps": (None, "25"),
            "width": (None, "1024"),
            "height": (None, "1024"),
            "guidance": (None, "4")
        },
        timeout=300
    )

    if not r.ok:
        raise Exception(f"Cloudflare HTTP {r.status_code}: {r.text[:300]}")

    image_base64 = r.json().get("result", {}).get("image")
    if not image_base64:
        raise Exception("Aucune image reçue de Cloudflare.")

    contenu = base64.b64decode(image_base64)
    resultat = sauvegarder_image(contenu)

    if not resultat:
        raise Exception("Format Cloudflare non reconnu.")

    return resultat


def ameliorer_prompt(prompt):
    cle = os.getenv("GROQ_API_KEY")
    if not cle:
        return prompt

    try:
        r = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {cle}",
                "Content-Type": "application/json"
            },
            json={
                "model": os.getenv("GROQ_MODEL", "openai/gpt-oss-120b"),
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "Tu es un directeur artistique professionnel. "
                            "Transforme la demande en un prompt visuel précis, "
                            "détaillé et professionnel pour un générateur d'images. "
                            "Respecte strictement le sujet, les couleurs, le style "
                            "et les détails demandés. Conserve exactement les noms, "
                            "numéros, slogans et textes entre guillemets. "
                            "N'invente aucune information. "
                            "Décris la composition, la lumière, le cadrage et "
                            "l'ambiance lorsque c'est utile. "
                            "Réponds uniquement avec le prompt final, sans explication."
                        )
                    },
                    {
                        "role": "user",
                        "content": prompt[:3000]
                    }
                ],
                "max_completion_tokens": 800,
                "reasoning_effort": "low",
                "include_reasoning": False
            },
            timeout=45
        )

        if not r.ok:
            return prompt

        choix = r.json().get("choices", [])
        resultat = (
            choix[0].get("message", {}).get("content")
            if choix else None
        )

        if isinstance(resultat, str) and resultat.strip():
            return resultat.strip()[:5000]

    except (requests.RequestException, ValueError, TypeError, KeyError, IndexError):
        pass

    return prompt


def generer_image(prompt):
    if not isinstance(prompt, str) or not prompt.strip():
        return "Erreur image : décris l'image souhaitée."

    prompt = ameliorer_prompt(prompt.strip())

    try:
        return generer_cloudflare(prompt)
    except Exception as erreur_cloud:
        try:
            return generer_pollinations(prompt)
        except Exception as erreur_polli:
            return (
                "Erreur FLUX.2 Dev : " + str(erreur_cloud)[:250]
                + " | Secours Pollinations : " + str(erreur_polli)[:250]
            )
