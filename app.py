# app.py
from Flask import Flask, render_template, request, redirect, url_for, flash

app = Flask(__name__)
app.secret_key = "votre_cle_secrete"

# Base de données fictive pour les utilisateurs
users_db = {}

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        email = request.form.get("email")
        username = request.form.get("username")
        password = request.form.get("password")

        # Vérification des champs obligatoires
        if not email or not username or not password:
            flash("Tous les champs sont obligatoires.", "error")
            return redirect(url_for("signup"))

        # Vérification de la complexité du mot de passe
        if len(password) < 8:
            flash("Le mot de passe doit contenir au moins 8 caractères.", "error")
            return redirect(url_for("signup"))

        # Vérification de l'unicité de l'email
        if email in users_db:
            flash("Cet email est déjà utilisé.", "error")
            return redirect(url_for("signup"))

        # Enregistrement de l'utilisateur
        users_db[email] = {"username": username, "password": password}
        flash("Compte créé avec succès !", "success")
        return redirect(url_for("timeline"))

    return render_template("signup.html")

@app.route("/timeline")
def timeline():
    return "Bienvenue sur votre timeline personnelle !"

if __name__ == "__main__":
    app.run(debug=True)

