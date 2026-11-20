import os
import secrets
from io import BytesIO
from pypdf import PdfReader
from openpyxl import load_workbook

from flask import Flask, render_template, request, jsonify

from cerveau import repondre
from image_generator import generer_image
from vision import analyser_photo
from video_generator import generer_video

app = Flask(__name__)

if not os.path.exists(".secret_key"):
    with open(".secret_key", "w") as f:
        f.write(secrets.token_hex(32))

with open(".secret_key") as f:
    app.config["SECRET_KEY"] = f.read().strip()

def demande_image(message):
    import unicodedata
    import re

    if not isinstance(message, str):
        return False

    texte = message.lower().replace("’", "'")
    texte = unicodedata.normalize("NFKD", texte)
    texte = "".join(
        c for c in texte if not unicodedata.combining(c)
    )
    texte = re.sub(r"[^a-z0-9 ]", " ", texte)
    texte = re.sub(r"\s+", " ", texte).strip()

    mots = set(texte.split())

    actions = {
        "genere", "generer", "cree", "creer",
        "dessine", "dessiner", "imagine",
        "fabrique", "produis", "produire",
        "realise", "concois"
    }

    objets = {
        "image", "images", "photo", "photos",
        "photographie", "illustration", "dessin",
        "logo", "avatar", "portrait", "affiche",
        "fond", "ecran", "wallpaper", "3d",
        "render", "visuel", "banniere"
    }

    if mots & actions:
        if mots & objets:
            return True

        if "dessine" in mots or "dessiner" in mots:
            return True

        if re.search(r"\b(genere|generer|cree|creer|imagine|fabrique)\b", texte):
            return True

    expressions_visuelles = [
        r"\bje veux voir\b",
        r"\bmontre moi\b",
        r"\bfais voir\b",
        r"\bfais moi une photo\b",
        r"\bfais moi une image\b",
        r"\bfais moi un dessin\b",
        r"\bje veux une image\b",
        r"\bje veux une photo\b",
        r"\btransforme moi en\b"
    ]

    if any(re.search(expression, texte) for expression in expressions_visuelles):
        return True

    return False


@app.route("/")
def accueil():
    return render_template("index.html")


@app.route("/application")
def application():
    return render_template("index.html")


@app.route("/chat", methods=["POST"])
def chat():
    try:
        photo = request.files.get("photo")

        if photo:
            if photo.mimetype not in (
                "image/jpeg", "image/png", "image/webp"
            ):
                return jsonify({
                    "response": "Format accepté : JPG, PNG ou WEBP."
                }), 400

            image = photo.read(8 * 1024 * 1024 + 1)

            if len(image) > 8 * 1024 * 1024:
                return jsonify({
                    "response": "La photo est trop volumineuse (8 Mo maximum)."
                }), 400

            if not image:
                return jsonify({"response": "Photo vide."}), 400

            message = request.form.get(
                "message",
                "Aide-moi à comprendre cet exercice."
            ).strip()

            reponse = analyser_photo(image, message)

            return jsonify({
                "response": reponse or "Je n'ai pas pu analyser la photo."
            })


        fichier = request.files.get("fichier")

        if fichier:
            nom = fichier.filename.lower()

            contenu = fichier.read(8 * 1024 * 1024 + 1)

            if len(contenu) > 8 * 1024 * 1024:
                return jsonify({"response": "Fichier trop volumineux : 8 Mo maximum."}), 400

            if nom.endswith(".pdf"):
                lecteur = PdfReader(BytesIO(contenu))
                texte = "\\n".join(
                    page.extract_text() or ""
                    for page in lecteur.pages[:10]
                )

            elif nom.endswith((".xlsx", ".xlsm")):
                classeur = load_workbook(
                    BytesIO(contenu),
                    read_only=True,
                    data_only=True
                )
                lignes = []

                for feuille in classeur.worksheets:
                    lignes.append("Feuille : " + feuille.title)
                    for ligne in feuille.iter_rows(max_row=100):
                        valeurs = [str(c.value or "") for c in ligne]
                        lignes.append(" | ".join(valeurs))

                texte = "\\n".join(lignes)
                classeur.close()

            else:
                return jsonify({"response": "Format accepté : PDF, XLSX ou XLSM."}), 400

            if not texte.strip():
                return jsonify({"response": "Je n'ai trouvé aucun texte lisible dans ce fichier."})

            message = request.form.get("message", "Analyse ce document et explique-moi son contenu.")

            reponse = repondre(
                message + "\\n\\nContenu du document :\\n" + texte[:12000]
            )

            return jsonify({"response": reponse})

        data = request.get_json(silent=True) or {}
        message = data.get("message", "")

        if not isinstance(message, str):
            return jsonify({"response": "Message invalide."}), 400

        message = message.strip()

        if not message:
            return jsonify({"response": "Écris un message."}), 400

        if len(message) > 4000:
            return jsonify({"response": "Ton message est trop long."}), 400

        if demande_image(message):
            resultat = generer_image(message)

            if not isinstance(resultat, str) or not resultat.startswith("/static/images/"):
                return jsonify({"response": resultat or "La génération a échoué."})

            return jsonify({
                "response": "Voici ton image générée par NEXORA AI !",
                "image": resultat
            })

        historique = data.get("historique", [])

        if not isinstance(historique, list):
            historique = []

        historique_valide = []

        for element in historique[-20:]:
            if not isinstance(element, dict):
                continue

            role = element.get("role")
            texte = element.get("texte", "")

            if role not in ("user", "bot"):
                continue

            if not isinstance(texte, str) or not texte.strip():
                continue

            historique_valide.append({
                "role": role,
                "texte": texte[:3000]
            })

        parametres = data.get("parametres", {})
        if not isinstance(parametres, dict):
            parametres = {}

        longueur = parametres.get("longueur")
        if longueur not in ("courte", "normale", "detaillee"):
            longueur = "normale"

        creativite = parametres.get("creativite")
        if creativite not in ("faible", "normale", "elevee"):
            creativite = "normale"

        if parametres.get("memoire") is False:
            historique_valide = []

        reponse = repondre(
            message,
            historique_valide,
            {"longueur": longueur, "creativite": creativite}
        )

        return jsonify({
            "response": reponse or "Je n'ai pas reçu de réponse."
        })

    except Exception:
        return jsonify({
            "response": "Une erreur est survenue. Réessaie."
        }), 500





@app.route("/creer-video", methods=["POST"])
def creer_video():
    data = request.get_json(silent=True) or {}

    prompt = data.get("prompt", "")
    duree = data.get("duree", 5)
    format_video = data.get("format", "paysage")

    if not isinstance(prompt, str) or not prompt.strip():
        return jsonify({"error": "Décris la vidéo à créer."}), 400

    try:
        duree = int(duree)
    except (TypeError, ValueError):
        return jsonify({"error": "Durée invalide. Choisis 2, 5 ou 8 secondes."}), 400

    if duree not in (2, 5, 8):
        return jsonify({"error": "Durées disponibles : 2, 5 ou 8 secondes."}), 400

    if format_video not in ("paysage", "portrait"):
        return jsonify({"error": "Format vidéo invalide."}), 400

    resultat = generer_video(prompt, duree, format_video)

    if "error" in resultat:
        return jsonify(resultat), 400

    return jsonify(resultat)

@app.route("/nouveau")
def nouveau():
    return render_template("nexora.html")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
