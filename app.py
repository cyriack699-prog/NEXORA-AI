import os
import secrets
import zipfile
from io import BytesIO
from pathlib import Path
from pypdf import PdfReader
from openpyxl import load_workbook

from flask import Flask, render_template, request, jsonify, send_file

from cerveau import repondre
from image_generator import generer_image
from vision import analyser_photo
from video_generator import generer_video
from developer import generer_projet, PROJECTS_DIR

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

    visuels = [
        r"\bimage(s)?\b",
        r"\bphoto(s)?\b",
        r"\bphotographie(s)?\b",
        r"\blogos?\b",
        r"\bdessin(s)?\b",
        r"\billustration(s)?\b",
        r"\bportrait(s)?\b",
        r"\bavatar(s)?\b",
        r"\baffiche(s)?\b",
        r"\bbanniere(s)?\b",
        r"\bwallpaper(s)?\b",
        r"\bfond d ecran\b",
        r"\brendu 3d\b",
    ]

    action_dessin = [
        r"\bdessine(r)?\b",
        r"\bpeins?\b",
        r"\billustre(r)?\b",
        r"\bgenere(r)?\b",
        r"\bcre(e|er)\b",
        r"\bfabrique(r)?\b",
        r"\brealise(r)?\b",
        r"\bproduis?\b",
    ]

    developpement = [
        r"\bapplication(s)?\b",
        r"\bapp(s)?\b",
        r"\bsite(s)? web\b",
        r"\bsite(s)? internet\b",
        r"\bpage(s)? web\b",
        r"\bprogramme(s)?\b",
        r"\bprogrammer\b",
        r"\bprogrammation\b",
        r"\bcode\b",
        r"\bcoder\b",
        r"\blogiciel(s)?\b",
        r"\bplateforme(s)?\b",
        r"\bbot(s)?\b",
    ]

    contient_visuel = any(re.search(p, texte) for p in visuels)
    contient_action = any(re.search(p, texte) for p in action_dessin)
    contient_developpement = any(
        re.search(p, texte) for p in developpement
    )

    if contient_visuel and contient_action:
        return True

    if contient_developpement:
        return False

    if re.search(r"\bdessine(r)?\b|\bpeins?\b|\billustre(r)?\b", texte):
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





@app.route("/developer", methods=["POST"])
def creer_projet():
    data = request.get_json(silent=True) or {}

    message = data.get("message", "")

    if not isinstance(message, str) or not message.strip():
        return jsonify({
            "success": False,
            "error": "Décris le projet que tu souhaites créer."
        }), 400

    if len(message) > 4000:
        return jsonify({
            "success": False,
            "error": "La description ne doit pas dépasser 4000 caractères."
        }), 400

    try:
        resultat = generer_projet(message.strip())

        if not resultat.get("success"):
            return jsonify(resultat), 502

        return jsonify(resultat)

    except Exception:
        app.logger.exception("Erreur lors de la création du projet")
        return jsonify({
            "success": False,
            "error": "Impossible de créer le projet pour le moment."
        }), 500


@app.route("/developer/download/<project_id>", methods=["GET"])
def telecharger_projet(project_id):

    if (
        len(project_id) != 12
        or any(c not in "0123456789abcdef" for c in project_id)
    ):
        return jsonify({
            "success": False,
            "error": "Identifiant de projet invalide."
        }), 400

    try:
        racine = PROJECTS_DIR.resolve()
        dossier = (racine / project_id).resolve(strict=True)

        if dossier.parent != racine or not dossier.is_dir():
            return jsonify({
                "success": False,
                "error": "Projet introuvable."
            }), 404

        archive = BytesIO()
        nombre_fichiers = 0
        taille_totale = 0

        with zipfile.ZipFile(
            archive,
            "w",
            compression=zipfile.ZIP_DEFLATED
        ) as zipf:

            for chemin in dossier.rglob("*"):

                if chemin.is_symlink():
                    return jsonify({
                        "success": False,
                        "error": "Lien symbolique interdit."
                    }), 400

                if not chemin.is_file():
                    continue

                destination = chemin.resolve(strict=True)

                if not destination.is_relative_to(dossier):
                    return jsonify({
                        "success": False,
                        "error": "Chemin de fichier interdit."
                    }), 400

                nombre_fichiers += 1
                taille_totale += destination.stat().st_size

                if nombre_fichiers > 30 or taille_totale > 1000000:
                    return jsonify({
                        "success": False,
                        "error": "Limites du projet dépassées."
                    }), 400

                nom_dans_zip = chemin.relative_to(dossier).as_posix()

                zipf.write(destination, nom_dans_zip)

        if nombre_fichiers == 0:
            return jsonify({
                "success": False,
                "error": "Ce projet ne contient aucun fichier."
            }), 404

        archive.seek(0)

        return send_file(
            archive,
            mimetype="application/zip",
            as_attachment=True,
            download_name=f"NEXORA-{project_id}.zip"
        )

    except FileNotFoundError:
        return jsonify({
            "success": False,
            "error": "Projet introuvable."
        }), 404

    except Exception:
        app.logger.exception("Erreur de création de l'archive ZIP")

        return jsonify({
            "success": False,
            "error": "Impossible de préparer le téléchargement."
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
