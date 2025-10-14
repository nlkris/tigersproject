from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
<<<<<<< HEAD
from utils.data_manager import read_users, write_users, read_tweets, write_tweets, init_files, ensure_likes_field, follow_user, unfollow_user
=======
from utils.data_manager import read_users, write_users, read_tweets, write_tweets, init_files, ensure_likes_field
from datetime import datetime
>>>>>>> 1d0325562ca5b08423fc335ed3acd9ac7f64f367

routes = Blueprint('routes', __name__)

# Initialisation des fichiers et champs
init_files()
ensure_likes_field()

# ------------------- ACCUEIL -------------------
@routes.route('/')
def home():
    return redirect(url_for('routes.login'))

# ------------------- INSCRIPTION -------------------
@routes.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()

        if not username or not email or not password:
            flash("Tous les champs sont obligatoires.", "error")
            return redirect(url_for('routes.signup'))

        if len(password) < 6:
            flash("Le mot de passe doit contenir au moins 6 caractères.", "error")
            return redirect(url_for('routes.signup'))

        users = read_users()
        if any(u['email'] == email for u in users):
            flash("Cet email est déjà utilisé.", "error")
            return redirect(url_for('routes.signup'))
        if any(u['username'].lower() == username.lower() for u in users):
            flash("Ce nom d'utilisateur est déjà pris.", "error")
            return redirect(url_for('routes.signup'))

        hashed_password = generate_password_hash(password)
        new_user = {
            'id': len(users) + 1,
            'username': username,
            'email': email,
            'password': hashed_password,
            'following': [],
            'followers': [],
            'profile_pic_url': None
        }
        users.append(new_user)
        write_users(users)
        flash("Inscription réussie ! Vous pouvez maintenant vous connecter.", "success")
        return redirect(url_for('routes.login'))

    return render_template('signup.html')

# ------------------- CONNEXION -------------------
@routes.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()

        users = read_users()
        user = next((u for u in users if u['email'] == email), None)

        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            flash("Connexion réussie !", "success")
            return redirect(url_for('routes.feed'))
        else:
            flash("Email ou mot de passe invalide.", "error")
            return redirect(url_for('routes.login'))

    return render_template('login.html')

# ------------------- FEED -------------------
@routes.route('/feed', methods=['GET', 'POST'])
def feed():
    if 'user_id' not in session:
        return redirect(url_for('routes.login'))

    tweets = read_tweets()
    users = read_users()

    # Publier un tweet
    if request.method == 'POST':
        content = request.form.get('content', '').strip()
        if content:
            new_tweet = {
                'id': len(tweets) + 1,
                'user_id': session['user_id'],
                'username': session['username'],
                'content': content,
                'likes': [],
                'reactions': {},
                'created_at': datetime.now().isoformat()
            }
            tweets.append(new_tweet)
            write_tweets(tweets)
            flash("Votre tweet a été publié !", "success")
            return redirect(url_for('routes.feed'))

    # Tri du plus récent au plus ancien
    tweets.sort(key=lambda t: t.get('created_at', ''), reverse=True)

    # Ajout systématique des champs pour le front
    for post in tweets:
        post.setdefault('likes', [])
        post.setdefault('reactions', {})
        post['liked'] = session['user_id'] in post['likes']

    # Pas de filtrage pour following/recommended → tous les tweets affichés immédiatement
    return render_template('feed.html', username=session['username'], tweets=tweets)

# ------------------- DÉCONNEXION -------------------
@routes.route('/logout')
def logout():
    session.clear()
    flash("Vous êtes déconnecté.", "info")
    return redirect(url_for('routes.login'))

# ------------------- LIKE -------------------
@routes.route('/like/<int:tweet_id>', methods=['POST'])
def like_tweet(tweet_id):
    if 'user_id' not in session:
        flash("Veuillez vous connecter pour liker un tweet.", "error")
        return redirect(url_for('routes.login'))

    tweets = read_tweets()
    user_id = session['user_id']

    for tweet in tweets:
        if tweet['id'] == tweet_id:
            tweet.setdefault('likes', [])
            if user_id in tweet['likes']:
                tweet['likes'].remove(user_id)
            else:
                tweet['likes'].append(user_id)
            write_tweets(tweets)
            break

    return redirect(request.referrer or url_for('routes.feed'))

# ------------------- RÉACTIONS MULTIPLES -------------------
@routes.route('/react/<int:tweet_id>/<emoji>', methods=['POST'])
def react(tweet_id, emoji):
    if 'user_id' not in session:
        return jsonify({"success": False, "message": "Non connecté"}), 401

    tweets = read_tweets()
    user_id = session['user_id']

    for tweet in tweets:
        if tweet['id'] == tweet_id:
            tweet.setdefault('reactions', {})
            tweet['reactions'].setdefault(emoji, [])

            if user_id in tweet['reactions'][emoji]:
                tweet['reactions'][emoji].remove(user_id)
            else:
                tweet['reactions'][emoji].append(user_id)

            write_tweets(tweets)
            return jsonify({"success": True, "count": len(tweet['reactions'][emoji])})

    return jsonify({"success": False, "message": "Tweet non trouvé"}), 404

# ------------------- PROFIL -------------------
@routes.route('/profile/<username>')
def profile(username):
    if 'user_id' not in session:
        return redirect(url_for('routes.login'))

    users = read_users()
    tweets = read_tweets()

    profile_user = next((u for u in users if u['username'] == username), None)
    if not profile_user:
        flash("Utilisateur introuvable.", "error")
        return redirect(url_for('routes.feed'))

    user_tweets = [t for t in tweets if t['username'] == username]
    user_tweets.sort(key=lambda t: t.get('created_at', ''), reverse=True)

    is_current_user = session.get('user_id') == profile_user['id']
    current_user = next((u for u in users if u['id'] == session.get('user_id')), None)
    is_following = profile_user['id'] in current_user.get('following', []) if current_user else False

    for post in user_tweets:
        post.setdefault('likes', [])
        post.setdefault('reactions', {})
        post['liked'] = session['user_id'] in post['likes']

    return render_template('profile.html',
                           profile_user=profile_user,
                           user_tweets=user_tweets,
                           is_current_user=is_current_user,
                           is_following=is_following)

# ------------------- SUIVRE / SE DÉSABONNER -------------------




# Route pour suivre un utilisateur
@app.route('/users/<int:user_id>/follow/<int:followed_id>', methods=['POST'])
def follow_user_route(user_id, followed_id):
    if follow_user(user_id, followed_id):
        return jsonify({
            'message': f"L'utilisateur {user_id} suit maintenant {followed_id}.",
            'success': True
        }), 200
    else:
        return jsonify({
            'error': "Impossible de suivre cet utilisateur (IDs invalides).",
            'success': False
        }), 404

# Route pour ne plus suivre un utilisateur
@app.route('/users/<int:user_id>/unfollow/<int:followed_id>', methods=['POST'])
def unfollow_user_route(user_id, followed_id):
    if unfollow_user(user_id, followed_id):
        return jsonify({
            'message': f"L'utilisateur {user_id} ne suit plus {followed_id}.",
            'success': True
        }), 200
    else:
        return jsonify({
            'error': "Impossible de ne plus suivre cet utilisateur (IDs invalides).",
            'success': False
        }), 404

# Route pour obtenir la liste des abonnements d'un utilisateur
@app.route('/users/<int:user_id>/following', methods=['GET'])
def get_following_route(user_id):
    following = get_following_details(user_id)
    return jsonify({
        'user_id': user_id,
        'following': following,
        'success': True
    }), 200

# Route pour obtenir la liste des abonnés d'un utilisateur
@app.route('/users/<int:user_id>/followers', methods=['GET'])
def get_followers_route(user_id):
    followers = get_followers_details(user_id)
    return jsonify({
        'user_id': user_id,
        'followers': followers,
        'success': True
    }), 200


# ------------------- SEARCH -------------------

=======
# ------------------- RECHERCHE -------------------
@routes.route('/search', methods=['GET'])
def search():
    if 'user_id' not in session:
        return redirect(url_for('routes.login'))

    query = request.args.get('q', '').strip()
    users = read_users()
    matched_users = [u for u in users if query.lower() in u['username'].lower()]

    return render_template('search.html', query=query, matched_users=matched_users)
