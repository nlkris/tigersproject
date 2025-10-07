from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
import json
import os

routes = Blueprint('routes', __name__)

# Chemins vers les fichiers JSON
DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')
USERS_FILE = os.path.join(DATA_DIR, 'users.json')
TWEETS_FILE = os.path.join(DATA_DIR, 'tweets.json')

# Initialisation des fichiers JSON
def init_files():
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)
    if not os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'w') as f:
            json.dump([], f)
    if not os.path.exists(TWEETS_FILE):
        with open(TWEETS_FILE, 'w') as f:
            json.dump([], f)

init_files()

# Fonctions utilitaires
def read_users():
    with open(USERS_FILE, 'r') as f:
        return json.load(f)

def write_users(users):
    with open(USERS_FILE, 'w') as f:
        json.dump(users, f, indent=4)

def read_tweets():
    with open(TWEETS_FILE, 'r') as f:
        return json.load(f)

def write_tweets(tweets):
    with open(TWEETS_FILE, 'w') as f:
        json.dump(tweets, f, indent=4)

# ------------------- ROUTES -------------------

@routes.route('/')
def home():
    return redirect(url_for('routes.login'))

@routes.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form.get('username').strip()
        email = request.form.get('email').strip()
        password = request.form.get('password').strip()

        if not username or not email or not password:
            flash("Tous les champs sont obligatoires.", "error")
            return redirect(url_for('routes.signup'))

        if len(password) < 6:
            flash("Le mot de passe doit contenir au moins 6 caractères.", "error")
            return redirect(url_for('routes.signup'))

        users = read_users()
        if any(user['email'] == email for user in users):
            flash("Cet email est déjà utilisé.", "error")
            return redirect(url_for('routes.signup'))
        if any(user['username'] == username for user in users):
            flash("Ce nom d'utilisateur est déjà utilisé.", "error")
            return redirect(url_for('routes.signup'))

        hashed_password = generate_password_hash(password)

        new_user = {
            'id': len(users) + 1,
            'username': username,
            'email': email,
            'password': hashed_password
        }
        users.append(new_user)
        write_users(users)

        flash("Inscription réussie ! Vous pouvez maintenant vous connecter.", "success")
        return redirect(url_for('routes.login'))

    return render_template('signup.html')

@routes.route('/login', methods=['GET', 'POST'])
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
            return redirect(url_for('routes.feed'))
        else:
            flash("Email ou mot de passe invalide.", "error")
            return redirect(url_for('routes.login'))

    return render_template('login.html')

@routes.route('/feed', methods=['GET', 'POST'])
def feed():
    if 'user_id' not in session:
        return redirect(url_for('routes.login'))

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
            return redirect(url_for('routes.feed'))

    return render_template('feed.html', tweets=tweets, username=session['username'])

@routes.route('/logout')
def logout():
    session.clear()
    flash("Vous êtes déconnecté.", "info")
    return redirect(url_for('routes.login'))
