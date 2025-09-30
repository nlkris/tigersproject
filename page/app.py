from flask import Flask, render_template, request, redirect, url_for, flash, session
import json
import os
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'votre_cle_secrete'  # Remplacez par une clé secrète sécurisée

# Chemins vers les fichiers JSON
USERS_FILE = 'data/users.json'
TWEETS_FILE = 'data/tweets.json'

# Initialisation des fichiers JSON si inexistants
def init_files():
    if not os.path.exists('data'):
        os.makedirs('data')
    if not os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'w') as f:
            json.dump([], f)
    if not os.path.exists(TWEETS_FILE):
        with open(TWEETS_FILE, 'w') as f:
            json.dump([], f)

init_files()

# Fonction pour lire les utilisateurs
def read_users():
    with open(USERS_FILE, 'r') as f:
        return json.load(f)

# Fonction pour écrire les utilisateurs
def write_users(users):
    with open(USERS_FILE, 'w') as f:
        json.dump(users, f, indent=4)

# Fonction pour lire les tweets
def read_tweets():
    with open(TWEETS_FILE, 'r') as f:
        return json.load(f)

# Fonction pour écrire les tweets
def write_tweets(tweets):
    with open(TWEETS_FILE, 'w') as f:
        json.dump(tweets, f, indent=4)

# Route pour la page d'inscription
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form.get('username').strip()
        email = request.form.get('email').strip()
        password = request.form.get('password').strip()

        # Vérification des champs obligatoires
        if not username or not email or not password:
            flash("Tous les champs sont obligatoires.", "error")
            return redirect(url_for('signup'))

        # Vérification de l'unicité de l'email et du nom d'utilisateur
        users = read_users()
        if any(user['email'] == email for user in users):
            flash("Cet email est déjà utilisé.", "error")
            return redirect(url_for('signup'))
        if any(user['username'] == username for user in users):
            flash("Ce nom d'utilisateur est déjà utilisé.", "error")
            return redirect(url_for('signup'))

        # Hachage du mot de passe
        hashed_password = generate_password_hash(password)

        # Ajout du nouvel utilisateur
        new_user = {
            'id': len(users) + 1,
            'username': username,
            'email': email,
            'password': hashed_password
        }
        users.append(new_user)
        write_users(users)

        flash("Inscription réussie ! Vous pouvez maintenant vous connecter.", "success")
        return redirect(url_for('login'))

    return render_template('signup.html')

# Route pour la page de connexion
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email').strip()
        password = request.form.get('password').strip()

        users = read_users()
        user = next((user for user in users if user['email'] == email), None)

        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            flash("Connexion réussie !", "success")
            return redirect(url_for('feed'))
        else:
            flash("Email ou mot de passe invalide.", "error")
            return redirect(url_for('login'))

    return render_template('login.html')

# Route pour la page d'accueil (feed)
@app.route('/feed', methods=['GET', 'POST'])
def feed():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    tweets = read_tweets()

    if request.method == 'POST':
        content = request.form.get('content').strip()
        if content:
            new_tweet = {
                'id': len(tweets) + 1,
                'user_id': session['user_id'],
                'username': session['username'],
                'content': content
            }
            tweets.append(new_tweet)
            write_tweets(tweets)
            flash("Votre tweet a été publié !", "success")
            return redirect(url_for('feed'))

    return render_template('feed.html', tweets=tweets, username=session['username'])

# Route pour la déconnexion
@app.route('/logout')
def logout():
    session.clear()
    flash("Vous êtes déconnecté.", "info")
    return redirect(url_for('login'))

# Route pour la page d'accueil
@app.route('/')
def home():
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
