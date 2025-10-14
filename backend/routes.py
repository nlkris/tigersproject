from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
from utils.data_manager import read_users, write_users, read_tweets, write_tweets, init_files, ensure_likes_field

routes = Blueprint('routes', __name__)

# Initialisation des fichiers et des champs manquants
init_files()
ensure_likes_field()

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
        if any(u['email'] == email for u in users):
            flash("Cet email est déjà utilisé.", "error")
            return redirect(url_for('routes.signup'))
        if any(u['username'] == username for u in users):
            flash("Ce nom d'utilisateur est déjà utilisé.", "error")
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


@routes.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email').strip()
        password = request.form.get('password').strip()

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


@routes.route('/feed', methods=['GET', 'POST'])
def feed():
    if 'user_id' not in session:
        return redirect(url_for('routes.login'))

    tweets = read_tweets()
    users = read_users()

    if request.method == 'POST':
        content = request.form.get('content').strip()
        if content:
            new_tweet = {
                'id': len(tweets) + 1,
                'user_id': session['user_id'],
                'username': session['username'],
                'content': content,
                'likes': []
            }
            tweets.append(new_tweet)
            write_tweets(tweets)
            flash("Votre tweet a été publié !", "success")
            return redirect(url_for('routes.feed'))

    # Fil d’actualité : tweets des utilisateurs que je suis
    current_user = next((u for u in users if u['id'] == session['user_id']), None)
    following_ids = current_user.get('following', []) if current_user else []
    following_feed = [t for t in tweets if t['user_id'] in following_ids]
    recommended_feed = [t for t in tweets if t['user_id'] not in following_ids and t['user_id'] != session['user_id']]

    # Ajouter info si le tweet est liké par l’utilisateur
    for post in following_feed + recommended_feed:
        post['liked'] = session['user_id'] in post.get('likes', [])

    return render_template('feed.html',
                           username=session['username'],
                           following_feed=following_feed,
                           recommended_feed=recommended_feed,
                           tweets=tweets)


@routes.route('/logout')
def logout():
    session.clear()
    flash("Vous êtes déconnecté.", "info")
    return redirect(url_for('routes.login'))


@routes.route('/like/<int:tweet_id>', methods=['POST'])
def like_tweet(tweet_id):
    if 'user_id' not in session:
        flash("Veuillez vous connecter pour liker un tweet.", "error")
        return redirect(url_for('routes.login'))

    tweets = read_tweets()
    user_id = session['user_id']

    for tweet in tweets:
        if tweet['id'] == tweet_id:
            if 'likes' not in tweet:
                tweet['likes'] = []

            if user_id in tweet['likes']:
                tweet['likes'].remove(user_id)
            else:
                tweet['likes'].append(user_id)

            write_tweets(tweets)
            break

    return redirect(request.referrer or url_for('routes.feed'))


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
    is_current_user = session.get('user_id') == profile_user['id']

    current_user = next((u for u in users if u['id'] == session.get('user_id')), None)
    is_following = profile_user['id'] in current_user.get('following', []) if current_user else False

    # Ajouter info si le tweet est liké
    for post in user_tweets:
        post['liked'] = session['user_id'] in post.get('likes', [])

    return render_template('profile.html',
                           profile_user=profile_user,
                           user_tweets=user_tweets,
                           is_current_user=is_current_user,
                           is_following=is_following)


@routes.route('/toggle_follow/<username>', methods=['POST'])
def toggle_follow(username):
    if 'user_id' not in session:
        flash("Veuillez vous connecter pour suivre ou se désabonner.", "error")
        return redirect(url_for('routes.login'))

    users = read_users()
    current_user = next((u for u in users if u['id'] == session['user_id']), None)
    target_user = next((u for u in users if u['username'] == username), None)

    if not target_user or not current_user:
        flash("Utilisateur introuvable.", "error")
        return redirect(url_for('routes.feed'))

    if 'following' not in current_user:
        current_user['following'] = []
    if 'followers' not in target_user:
        target_user['followers'] = []

    if target_user['id'] in current_user['following']:
        current_user['following'].remove(target_user['id'])
        target_user['followers'].remove(current_user['id'])
        flash(f"Vous avez cessé de suivre {username}.", "info")
    else:
        current_user['following'].append(target_user['id'])
        target_user['followers'].append(current_user['id'])
        flash(f"Vous suivez maintenant {username}.", "success")

    write_users(users)
    return redirect(request.referrer or url_for('routes.profile', username=username))


# ------------------- SEARCH -------------------

@routes.route('/search', methods=['GET'])
def search():
    if 'user_id' not in session:
        return redirect(url_for('routes.login'))

    query = request.args.get('q', '').strip()
    users = read_users()
    matched_users = [u for u in users if query.lower() in u['username'].lower()]

    return render_template('search.html', query=query, matched_users=matched_users)
