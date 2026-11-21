import os
import re
import json
import uuid
import logging
from pathlib import Path

import requests
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
PROJECTS_DIR = BASE_DIR / "projects"

load_dotenv(BASE_DIR / ".env")

SYSTEME_DEVELOPPEUR = """
Tu es le moteur de développement logiciel de NEXORA AI.

Ta mission est de créer de véritables projets informatiques.

Tu dois comprendre la demande et produire un projet cohérent,
complet et fonctionnel.

Tu peux créer des sites web, applications, programmes Python,
interfaces, outils et autres logiciels.

RÈGLES :
- Génère du véritable code, pas des explications.
- Organise correctement les fichiers.
- Utilise des noms de fichiers explicites.
- Produis un code propre, structuré et commenté lorsque nécessaire.
- Respecte précisément la demande.
- Pour un site web, sépare HTML, CSS et JavaScript.
- N'inclus jamais de clé API, mot de passe ou secret.
- Ne prétends pas avoir testé ou exécuté le projet.
- Ne crée pas de fichiers inutiles.

FORMAT OBLIGATOIRE :
Réponds uniquement avec un objet JSON valide :

{
  "name": "Nom du projet",
  "description": "Description du projet",
  "files": [
    {
      "path": "index.html",
      "content": "Contenu complet du fichier"
    },
    {
      "path": "style.css",
      "content": "Contenu complet du fichier"
    }
  ]
}

Aucun texte avant ou après le JSON.
"""


def appeler_ia(messages):
    groq_key = os.getenv("GROQ_API_KEY")

    if groq_key:
        try:
            reponse = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {groq_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": os.getenv(
                        "GROQ_MODEL",
                        "openai/gpt-oss-120b"
                    ),
                    "messages": messages,
                    "max_completion_tokens": 12000,
                    "reasoning_effort": "low",
                    "include_reasoning": False
                },
                timeout=180
            )

            if reponse.ok:
                resultat = reponse.json()
                choix = resultat.get("choices", [])

                if choix:
                    contenu = choix[0].get(
                        "message", {}
                    ).get("content")

                    if isinstance(contenu, str) and contenu.strip():
                        return contenu.strip()

        except (requests.RequestException, ValueError, TypeError):
            logging.exception("Échec du moteur Groq développeur")

    account_id = os.getenv("CLOUDFLARE_ACCOUNT_ID")
    token = os.getenv("CLOUDFLARE_API_TOKEN")

    if account_id and token:
        try:
            url = (
                "https://api.cloudflare.com/client/v4/accounts/"
                + account_id
                + "/ai/run/@cf/meta/llama-3.3-70b-instruct-fp8-fast"
            )

            reponse = requests.post(
                url,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json"
                },
                json={
                    "messages": messages,
                    "max_tokens": 12000
                },
                timeout=180
            )

            reponse.raise_for_status()
            resultat = reponse.json()

            contenu = resultat.get(
                "result", {}
            ).get("response")

            if isinstance(contenu, str) and contenu.strip():
                return contenu.strip()

        except (requests.RequestException, ValueError, TypeError):
            logging.exception("Échec du moteur Cloudflare développeur")

    raise RuntimeError(
        "Aucun fournisseur IA n'a pu générer le projet."
    )


def extraire_json(texte):
    texte = texte.strip()

    texte = re.sub(
        r"^```(?:json)?\s*",
        "",
        texte,
        flags=re.IGNORECASE
    )

    texte = re.sub(r"\s*```$", "", texte)

    debut = texte.find("{")
    fin = texte.rfind("}")

    if debut == -1 or fin == -1:
        raise ValueError("La réponse IA ne contient pas de JSON.")

    return json.loads(texte[debut:fin + 1])


def valider_fichiers(fichiers):
    if not isinstance(fichiers, list) or not fichiers:
        raise ValueError("Le projet ne contient aucun fichier.")

    if len(fichiers) > 30:
        raise ValueError("Le projet contient trop de fichiers.")

    resultat = []
    total = 0
    chemins_vus = set()

    for fichier in fichiers:
        if not isinstance(fichier, dict):
            raise ValueError("Structure de fichier invalide.")

        chemin = fichier.get("path")
        contenu = fichier.get("content")

        if not isinstance(chemin, str):
            raise ValueError("Nom de fichier invalide.")

        if not isinstance(contenu, str):
            raise ValueError("Contenu de fichier invalide.")

        chemin = chemin.replace("\\", "/")

        if (
            not chemin
            or chemin.startswith("/")
            or "\x00" in chemin
            or any(part in ("", ".", "..") for part in chemin.split("/"))
        ):
            raise ValueError("Chemin de fichier interdit.")

        if len(chemin) > 180:
            raise ValueError("Chemin de fichier trop long.")

        if re.match(r"^[a-zA-Z]:", chemin):
            raise ValueError("Chemin absolu interdit.")

        if chemin.lower() in (
            ".env",
            ".secret_key",
            ".git",
            "id_rsa"
        ):
            raise ValueError("Nom de fichier protégé.")

        if any(part.startswith(".") for part in chemin.split("/")):
            raise ValueError("Les fichiers cachés sont interdits.")

        if chemin in chemins_vus:
            raise ValueError("Deux fichiers portent le même nom.")

        taille = len(contenu.encode("utf-8"))

        if taille > 200000:
            raise ValueError("Un fichier dépasse 200 Ko.")

        total += taille

        if total > 1000000:
            raise ValueError("Le projet dépasse 1 Mo.")

        chemins_vus.add(chemin)

        resultat.append({
            "path": chemin,
            "content": contenu
        })

    return resultat


def generer_projet(description):
    if not isinstance(description, str):
        return {
            "success": False,
            "error": "Description invalide."
        }

    description = description.strip()

    if not description:
        return {
            "success": False,
            "error": "Décris le projet à créer."
        }

    if len(description) > 4000:
        return {
            "success": False,
            "error": "La description est trop longue."
        }

    try:
        messages = [
            {
                "role": "system",
                "content": SYSTEME_DEVELOPPEUR
            },
            {
                "role": "user",
                "content": description
            }
        ]

        texte = appeler_ia(messages)
        projet = extraire_json(texte)

        nom = projet.get("name", "Projet NEXORA")
        details = projet.get("description", "")

        if not isinstance(nom, str) or not nom.strip():
            nom = "Projet NEXORA"

        if not isinstance(details, str):
            details = ""

        fichiers = valider_fichiers(projet.get("files"))

        identifiant = uuid.uuid4().hex[:12]

        dossier = PROJECTS_DIR / identifiant
        dossier.mkdir(parents=True, exist_ok=False)

        for fichier in fichiers:
            destination = dossier / fichier["path"]

            destination.parent.mkdir(
                parents=True,
                exist_ok=True
            )

            destination.write_text(
                fichier["content"],
                encoding="utf-8"
            )

        return {
            "success": True,
            "project_id": identifiant,
            "name": nom.strip()[:100],
            "description": details[:1000],
            "files": [
                {
                    "path": fichier["path"],
                    "content": fichier["content"]
                }
                for fichier in fichiers
            ]
        }

    except Exception as erreur:
        logging.exception("Erreur de génération de projet NEXORA")

        return {
            "success": False,
            "error": str(erreur)[:300]
        }
