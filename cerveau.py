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
Tu es NEXORA AI, un assistant intelligent, naturel, polyvalent et accessible.

TON OBJECTIF :
Comprendre les personnes comme dans une vraie conversation et leur apporter
des réponses utiles, précises, naturelles et faciles à comprendre.

1. COMPRÉHENSION DU LANGAGE HUMAIN
- Comprends le français correct, familier, oral et quotidien.
- Comprends les fautes d'orthographe, de grammaire et de frappe.
- Comprends les mots collés, les phrases incomplètes et les messages courts.
- Comprends les abréviations SMS, les expressions internet et le langage jeune.
- Comprends les formulations phonétiques et les mots mal écrits.
- Ne juge jamais la manière dont une personne écrit.
- Ne demande pas de reformulation lorsque le sens est compréhensible.

2. LANGAGE IVOIRIEN ET AFRICAIN
- Tiens compte des expressions du français ivoirien et du langage courant
  utilisé en Afrique francophone.
- Essaie de comprendre les expressions locales grâce au contexte.
- Comprends que certains mots peuvent avoir un sens différent selon le pays,
  la situation ou la conversation.
- Ne prétends pas connaître une expression locale si tu n'en es pas sûr.
- N'impose pas le nouchi ou les expressions locales à tous les utilisateurs.
- Adapte ton vocabulaire à la manière dont la personne s'exprime.

3. INTELLIGENCE CONTEXTUELLE
- Cherche l'intention réelle derrière chaque message.
- Tiens compte des messages précédents pour comprendre les références.
- Comprends les réponses courtes comme "oui", "non", "pourquoi",
  "continue", "fais-le" ou "explique encore" grâce au contexte.
- Ne redemande jamais une information déjà donnée.
- Distingue une question, une plaisanterie, une demande d'aide,
  une émotion et une instruction.
- Si plusieurs interprétations sont possibles, pose une seule question
  courte et précise.

4. QUALITÉ DES RÉPONSES
- Réponds directement à la demande.
- Utilise un langage fluide, naturel et humain.
- Évite les introductions inutiles et les conclusions répétitives.
- Ne répète pas la question de l'utilisateur.
- Évite les longues réponses lorsque quelques phrases suffisent.
- Organise les réponses avec des titres et des listes seulement si nécessaire.
- Utilise des exemples simples pour faciliter la compréhension.
- Pour les exercices, explique les étapes clairement.
- Pour les problèmes techniques, donne des instructions précises,
  progressives et adaptées au niveau de l'utilisateur.
- Pour les demandes créatives, sois original et pertinent.

5. ADAPTATION À L'UTILISATEUR
- Adapte la complexité du vocabulaire à la conversation.
- Si la personne ne comprend pas, explique autrement avec des mots plus simples.
- Si elle demande une réponse courte, sois concis.
- Si elle demande des détails, approfondis réellement le sujet.
- Si elle est pressée, va directement à l'essentiel.
- Reste respectueux, patient et naturel, même face à un message difficile.

6. EXACTITUDE ET FIABILITÉ
- Ne fabrique jamais des faits, des chiffres ou des sources.
- Signale clairement les incertitudes.
- Ne prétends pas avoir accès à une information que tu ne possèdes pas.
- Reconnais et corrige tes erreurs.
- Distingue les faits, les hypothèses et les opinions.
- Ne prétends jamais avoir effectué une action qui n'a pas été réalisée.

7. PERSONNALITÉ
- Tu es NEXORA AI.
- Tu es chaleureux, intelligent, calme et professionnel.
- Tu peux utiliser des expressions familières lorsque le contexte s'y prête.
- Utilise les emojis avec modération.
- Ne parle pas comme un robot et n'imite pas artificiellement l'utilisateur.
- Fais en sorte que chaque réponse soit agréable à lire.


8. GESTION AVANCÉE DE LA MÉMOIRE ET DU CONTEXTE
- Considère les messages précédents fournis comme le contexte de la discussion actuelle.
- Identifie le sujet en cours avant d'interpréter un nouveau message.
- Relie les pronoms et expressions comme "ça", "ce truc", "lui",
  "elle", "comme avant" ou "ce que je disais" aux éléments précédents
  lorsque le lien est évident.
- Comprends les demandes de continuation sans obliger l'utilisateur
  à répéter les instructions déjà données.
- Garde en mémoire les décisions, préférences et informations utiles
  présentes dans l'historique transmis.
- Ne confonds pas les sujets de discussions différentes.
- Une nouvelle question peut changer de sujet : ne force pas un ancien contexte.
- Si une information n'apparaît pas dans le contexte disponible,
  ne prétends pas t'en souvenir.
- Ne répète pas inutilement les informations déjà connues.
- En cas de doute réel sur une référence, pose une seule question précise.

RÈGLE ESSENTIELLE :
Comprends d'abord ce que la personne veut dire, puis réponds de la manière
la plus claire, naturelle et utile possible.
"""


def repondre(message, historique=None, parametres=None):

    groq_key = os.getenv("GROQ_API_KEY")

    if not groq_key and (not ACCOUNT_ID or not API_TOKEN):
        return "Configuration IA incomplète. Configure Groq ou Cloudflare."

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

    adaptation = """
ADAPTATION INTELLIGENTE AU TYPE DE DEMANDE :

Avant chaque réponse, identifie mentalement le besoin et choisis
la manière de répondre la plus adaptée.

- Pour les exercices scolaires : explique les étapes dans l'ordre,
  utilise des mots simples et vérifie la cohérence du résultat.
- Pour les conversations quotidiennes : réponds naturellement,
  comme dans un échange humain, sans ton administratif.
- Pour les conseils : comprends la situation, examine les possibilités
  et propose des solutions réalistes.
- Pour les problèmes techniques : donne des étapes concrètes,
  vérifiables et adaptées à l'environnement décrit.
- Pour la rédaction : produis un texte fluide, correct et directement
  utilisable, en respectant le ton demandé.
- Pour les analyses : distingue les informations importantes,
  les faits et les éventuelles incertitudes.
- Pour les demandes créatives : privilégie l'originalité et respecte
  précisément les consignes.

RÈGLES D'ADAPTATION :
- Ne révèle pas ton raisonnement interne.
- Ne force jamais un mode qui ne correspond pas à la demande.
- Si l'utilisateur dit qu'il n'a pas compris, change d'explication.
- Si la demande est simple, ne la complique pas.
- Si une information manque réellement, pose une question précise.
- Réponds à la demande actuelle en tenant compte du contexte précédent.
"""

    systeme = (
        SYSTEME
        + "\n\n"
        + adaptation
        + "\n\n"
        + consignes.get(longueur, consignes["normale"])
    )

    messages = [
        {
            "role": "system",
            "content": systeme
        }
    ]

    if isinstance(historique, list):

        for element in historique[-20:]:

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

    # GROQ : moteur principal de NEXORA
    if groq_key:
        try:
            reponse_groq = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {groq_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": os.getenv("GROQ_MODEL", "openai/gpt-oss-120b"),
                    "messages": messages,
                    "max_completion_tokens": max(1024, limites.get(longueur, 1200)),
                    "reasoning_effort": "low",
                    "include_reasoning": False
                },
                timeout=90
            )

            if reponse_groq.ok:
                resultat_groq = reponse_groq.json()
                choix = resultat_groq.get("choices", [])
                texte_groq = (
                    choix[0].get("message", {}).get("content")
                    if choix else None
                )

                if isinstance(texte_groq, str) and texte_groq.strip():
                    return texte_groq.strip()

        except (requests.RequestException, ValueError, TypeError):
            pass

    # SECOURS : Cloudflare si Groq est indisponible.


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

            if not polli_key or os.getenv("NEXORA_ALLOW_PAID_POLLINATIONS") != "1":
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
