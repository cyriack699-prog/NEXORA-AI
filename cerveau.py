import os
import requests
from dotenv import load_dotenv

load_dotenv()

ACCOUNT_ID = os.getenv("CLOUDFLARE_ACCOUNT_ID")
API_TOKEN = os.getenv("CLOUDFLARE_API_TOKEN")

URL = (
    f"https://api.cloudflare.com/client/v4/accounts/"
    f"{ACCOUNT_ID}/ai/run/@cf/meta/llama-3.3-70b-instruct-fp8-fast"
) if ACCOUNT_ID else None


SYSTEME = """
Tu es NEXORA AI, un assistant intelligent, moderne et performant.

IDENTITÉ :
Tu es NEXORA, une intelligence artificielle conçue pour aider,
expliquer, analyser, réfléchir et accompagner les utilisateurs.

COMPORTEMENT :
- Réponds dans la langue de l'utilisateur.
- Sois naturel, intelligent et respectueux.
- Comprends le contexte de la conversation.
- Évite les répétitions inutiles.
- Ne demande pas des informations déjà fournies.
- Donne des réponses précises et utiles.
- Explique les sujets complexes étape par étape.
- Adapte ton vocabulaire au niveau de l'utilisateur.
- Utilise des exemples lorsque cela facilite la compréhension.
- Reconnais tes erreurs et corrige-les.
- Ne fabrique jamais de fausses informations.
- Ne prétends jamais avoir effectué une action non réalisée.

RAISONNEMENT :
- Analyse la demande avant de répondre.
- Identifie précisément le besoin.
- Tiens compte des messages précédents.
- Privilégie les solutions concrètes.
- Si plusieurs solutions existent, présente la meilleure.

COMPRÉHENSION INTELLIGENTE ET CORRECTION MENTALE :
- Comprends les messages même s'ils contiennent des fautes d'orthographe,
  de grammaire, de conjugaison ou de frappe.
- Reconnais les mots déformés, les lettres oubliées, les espaces manquants,
  les mots collés et les phrases écrites phonétiquement.
- Comprends les phrases courtes, incomplètes, désordonnées ou familières.
- Utilise le contexte de la conversation pour retrouver le sens probable.
- Interprète l'intention de l'utilisateur plutôt que de te bloquer sur
  la forme exacte de ses mots.
- Exemples :
  "tu pe maidé" signifie "Tu peux m'aider ?"
  "je compran pa" signifie "Je ne comprends pas."
  "g pa compri" signifie "Je n'ai pas compris."
  "c koi sa" signifie "C'est quoi ça ?"
  "tu fé komen" signifie "Tu fais comment ?"
  "sa marche pa" signifie "Ça ne marche pas."
- Ne critique jamais l'orthographe de l'utilisateur.
- Ne demande pas de réécrire si le sens est suffisamment clair.
- Si plusieurs interprétations sont possibles, pose une seule question
  courte pour clarifier.
- Réponds directement à l'intention comprise, avec un français naturel,
  clair et facile à comprendre.

COMPRÉHENSION DU LANGAGE SMS :
- Comprends automatiquement les abréviations et expressions SMS.
- Interprète les messages même avec des fautes ou sans ponctuation.
- Exemples : cc = coucou, bjr = bonjour, bsr = bonsoir,
  cv = ça va, jsp = je ne sais pas, tkt = ne t'inquiète pas,
  mrc = merci, stp = s'il te plaît, pq = pourquoi,
  psk = parce que, bcp = beaucoup, jtm = je t'aime,
  mdr = mort de rire, jpp = je n'en peux plus.
- Comprends aussi le langage jeune, les expressions internet,
  les abréviations anglaises et le langage courant ivoirien.
- Utilise le contexte pour comprendre les abréviations ambiguës.
- Ne demande pas systématiquement à l'utilisateur de reformuler.
- Réponds naturellement sans corriger inutilement son écriture.

IDENTITÉ VISUELLE :
Utilise occasionnellement des emojis adaptés.
Garde un style moderne, professionnel et agréable.
"""


def repondre(message, historique=None, parametres=None):

    if not ACCOUNT_ID or not API_TOKEN:
        return "Configuration IA incomplète. Vérifie les identifiants Cloudflare."

    if not isinstance(message, str) or not message.strip():
        return "Écris un message pour commencer."

    parametres = parametres if isinstance(parametres, dict) else {}

    longueur = parametres.get("longueur", "normale")
    creativite = parametres.get("creativite", "normale")

    limites = {
        "courte": 500,
        "normale": 1200,
        "detaillee": 2000
    }

    temperatures = {
        "faible": 0.2,
        "normale": 0.7,
        "elevee": 1.0
    }

    consignes = {
        "courte": "Réponds de manière courte et directe.",
        "normale": "Donne une réponse équilibrée et claire.",
        "detaillee": "Donne une réponse détaillée et bien expliquée."
    }

    systeme = SYSTEME + "\n\n" + consignes.get(
        longueur, consignes["normale"]
    )

    messages = [
        {
            "role": "system",
            "content": systeme
        }
    ]

    if isinstance(historique, list):

        for element in historique[-12:]:

            if not isinstance(element, dict):
                continue

            role = element.get("role")
            contenu = element.get("texte", "")

            if role not in ("user", "bot"):
                continue

            if not isinstance(contenu, str):
                continue

            contenu = contenu.strip()

            if not contenu:
                continue

            messages.append({
                "role": "user" if role == "user" else "assistant",
                "content": contenu[:3000]
            })

    messages.append({
        "role": "user",
        "content": message.strip()[:5000]
    })

    donnees = {
        "messages": messages,
        "max_tokens": limites.get(longueur, 1200),
        "temperature": temperatures.get(creativite, 0.7)
    }

    try:

        reponse = requests.post(
            URL,
            headers={
                "Authorization": f"Bearer {API_TOKEN}",
                "Content-Type": "application/json"
            },
            json=donnees,
            timeout=90
        )

        if reponse.status_code == 401:
            return "Erreur : le jeton Cloudflare n'est pas accepté."

        if reponse.status_code == 404:
            return "Erreur : le modèle IA demandé est introuvable."

        if reponse.status_code == 429:
            polli_key = os.getenv("POLLINATIONS_API_KEY")

            if not polli_key:
                return "Cloudflare est limité et Pollinations n'est pas configuré."

            try:
                secours = requests.post(
                    "https://gen.pollinations.ai/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {polli_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "openai/gpt-5.4-nano",
                        "messages": messages,
                        "max_tokens": limites.get(longueur, 1200)
                    },
                    timeout=90
                )

                secours.raise_for_status()
                resultat_polli = secours.json()
                choix = resultat_polli.get("choices", [])
                texte = (
                    choix[0].get("message", {}).get("content")
                    if choix else None
                )

                if isinstance(texte, str) and texte.strip():
                    return texte.strip()

                return "Pollinations n'a pas fourni de réponse."

            except requests.RequestException:
                return "Cloudflare est limité et Pollinations est momentanément indisponible."
            except (ValueError, KeyError, IndexError, TypeError):
                return "Erreur lors de la réception de la réponse Pollinations."

        try:
            resultat = reponse.json()
        except ValueError:
            resultat = {}

        if resultat.get("success") is False:
            erreurs = resultat.get("errors", [])
            codes = [
                str(erreur.get("code", ""))
                for erreur in erreurs
                if isinstance(erreur, dict)
            ]

            if "8007" in codes:
                return (
                    "Cloudflare a bloqué ce message avec son filtre "
                    "de sécurité. Essaie de reformuler ta demande."
                )

            return "Le service IA a refusé la requête. Réessaie."

        reponse.raise_for_status()

        texte = resultat.get("result", {}).get("response")

        if not isinstance(texte, str) or not texte.strip():
            return "L'IA n'a pas fourni de réponse. Réessaie."

        return texte.strip()

    except requests.exceptions.Timeout:
        return "Le serveur IA met trop de temps à répondre."

    except requests.exceptions.ConnectionError:
        return "Impossible de joindre le serveur IA. Vérifie Internet."

    except requests.exceptions.HTTPError:
        return "Le service Cloudflare a rencontré une erreur."

    except (ValueError, KeyError, TypeError):
        return "La réponse reçue du service IA est invalide."

    except Exception:
        return "Une erreur inattendue est survenue."
