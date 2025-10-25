from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from utils.data_manager import read_users, write_users, read_tweets, write_tweets, init_files, ensure_likes_field, ensure_follow_fields
from datetime import datetime

routes = Blueprint('routes', __name__)

# Initialisation des fichiers et champs
init_files()
ensure_likes_field()
ensure_follow_fields()

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
    current_user_id = session['user_id']
    current_user = next((u for u in users if u['id'] == current_user_id), None)

    # Publier un tweet
    if request.method == 'POST':
        content = request.form.get('content', '').strip()
        if content:
            new_tweet = {
                'id': len(tweets) + 1,
                'user_id': current_user_id,
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
        post['liked'] = current_user_id in post['likes']

    # --- Gestion des catégories ---
    followed_ids = current_user.get('following', [])

    # Tweets des abonnements + les siens
    followed_tweets = [t for t in tweets if t['user_id'] in followed_ids or t['user_id'] == current_user_id]

    # Tweets recommandés (non suivis et non soi-même)
    recommended_tweets = [t for t in tweets if t['user_id'] not in followed_ids and t['user_id'] != current_user_id]

    # Vue active : abonnements ou recommandations
    view = request.args.get('view', 'followed')

    return render_template(
        'feed.html',
        username=session['username'],
        view=view,
        followed_tweets=followed_tweets,
        recommended_tweets=recommended_tweets
    )



# ------------------- DÉCONNEXION -------------------
@routes.route('/logout')
def logout():
    session.clear()
    flash("Vous êtes déconnecté.", "info")
    return redirect(url_for('routes.login'))


# ------------------- LIKE JSON -------------------
@routes.route('/like/<int:tweet_id>', methods=['POST'])
def like_tweet(tweet_id):
    if 'user_id' not in session:
        return jsonify({"success": False, "message": "Non connecté"}), 401

    tweets = read_tweets()
    user_id = session['user_id']

    for tweet in tweets:
        if tweet['id'] == tweet_id:
            tweet.setdefault('likes', [])
            if user_id in tweet['likes']:
                tweet['likes'].remove(user_id)
                liked = False
            else:
                tweet['likes'].append(user_id)
                liked = True
            write_tweets(tweets)
            return jsonify({"success": True, "liked": liked, "like_count": len(tweet['likes'])})

    return jsonify({"success": False, "message": "Tweet non trouvé"}), 404



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

    # Ajout systématique des champs pour le front
    for post in user_tweets:
        post.setdefault('likes', [])
        post.setdefault('reactions', {})
        post['liked'] = session['user_id'] in post['likes']

    # --- Nouveaux : listes complètes d'objets utilisateurs pour abonnés / abonnements ---
    followers_list = [u for u in users if u['id'] in profile_user.get('followers', [])]
    following_list = [u for u in users if u['id'] in profile_user.get('following', [])]

    return render_template(
        'profile.html',
        profile_user=profile_user,
        user_tweets=user_tweets,
        is_current_user=is_current_user,
        is_following=is_following,
        followers_list=followers_list,
        following_list=following_list
    )

# ------------------- SUIVRE / SE DÉSABONNER -------------------
@routes.route('/toggle_follow/<username>', methods=['POST'])
def toggle_follow(username):
    if 'user_id' not in session:
        return jsonify({'error': 'Non connecté'}), 401

    users = read_users()
    current_user_id = session['user_id']

    current_user = next((u for u in users if u['id'] == current_user_id), None)
    target_user = next((u for u in users if u['username'] == username), None)

    if not current_user or not target_user:
        return jsonify({'error': 'Utilisateur introuvable'}), 404

    current_user.setdefault('following', [])
    target_user.setdefault('followers', [])

    if target_user['id'] in current_user['following']:
        current_user['following'].remove(target_user['id'])
        if current_user['id'] in target_user['followers']:
            target_user['followers'].remove(current_user['id'])
        is_following = False
    else:
        current_user['following'].append(target_user['id'])
        if current_user['id'] not in target_user['followers']:
            target_user['followers'].append(current_user['id'])
        is_following = True

    write_users(users)

    return jsonify({
        'is_following': is_following,
        'followers_count': len(target_user['followers']),
        'following_count': len(current_user['following'])
    })


# ------------------- RECHERCHE -------------------
@routes.route('/search_ajax')
def search_ajax():
    if 'user_id' not in session:
        return jsonify([])

    query = request.args.get('q', '').strip()
    users = read_users()
    matched_users = [
        {'username': u['username'], 'followers_count': len(u.get('followers', []))}
        for u in users if query.lower() in u['username'].lower()
    ]
    return jsonify(matched_users)

