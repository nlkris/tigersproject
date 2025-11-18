from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify, send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from utils.data_manager import read_users, write_users, read_tweets, write_tweets, init_files, ensure_likes_field, ensure_follow_fields
from datetime import datetime
import os

routes = Blueprint('routes', __name__)

UPLOAD_FOLDER = os.path.join(os.getcwd(), "backend", "uploads", "profile_pics")
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Initialisation des fichiers
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
            'profile_pic_url': None,
            'bio': ''
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

    # POST d'un nouveau tweet
    if request.method == 'POST':
        content = request.form.get('content', '').strip()
        if content:
            new_tweet = {
                'id': len(tweets) + 1,
                'user_id': current_user_id,
                'username': session['username'],
                'content': content,
                'likes': [],
                'created_at': datetime.now().isoformat()
            }
            tweets.append(new_tweet)
            write_tweets(tweets)
            flash("Votre tweet a été publié !", "success")
            return redirect(url_for('routes.feed'))

    # Tri et ajout du champ liked
    tweets.sort(key=lambda t: t.get('created_at', ''), reverse=True)
    for post in tweets:
        post.setdefault('likes', [])
        post['liked'] = current_user_id in post['likes']

    followed_ids = current_user.get('following', [])
    followed_tweets = [t for t in tweets if t['user_id'] in followed_ids or t['user_id'] == current_user_id]
    recommended_tweets = [t for t in tweets if t['user_id'] not in followed_ids and t['user_id'] != current_user_id]

    view = request.args.get('view', 'followed')

    return render_template(
        'feed.html',
        username=session['username'],
        view=view,
        followed_tweets=followed_tweets,
        recommended_tweets=recommended_tweets,
        users=users,
        current_user=current_user
    )

# ------------------- LOGOUT -------------------
@routes.route('/logout')
def logout():
    session.clear()
    flash("Vous avez été déconnecté.", "success")
    return redirect(url_for('routes.login'))

# ------------------- LIKE -------------------
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

# ------------------- TOGGLE FOLLOW -------------------
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

    user_tweets = [t for t in tweets if t['user_id'] == profile_user['id']]
    user_tweets.sort(key=lambda t: t.get('created_at', ''), reverse=True)

    current_user = next((u for u in users if u['id'] == session.get('user_id')), None)
    is_current_user = current_user['id'] == profile_user['id']
    is_following = profile_user['id'] in current_user.get('following', []) if current_user else False

    for post in user_tweets:
        post.setdefault('likes', [])
        post['liked'] = session['user_id'] in post['likes']

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

# ------------------- EDIT PROFILE -------------------
@routes.route('/profile/edit', methods=['POST'])
def edit_profile():
    if 'user_id' not in session:
        flash("Vous devez être connecté pour modifier un profil.", "error")
        return redirect(url_for('routes.login'))

    users = read_users()
    tweets = read_tweets()
    current_user_id = session['user_id']
    user = next((u for u in users if u['id'] == current_user_id), None)

    if not user:
        flash("Utilisateur introuvable.", "error")
        return redirect(url_for('routes.profile', username=session.get('username')))

    new_username = request.form.get('username', '').strip()
    new_bio = request.form.get('bio', '').strip()

    if new_username != user['username'] and any(u['username'].lower() == new_username.lower() for u in users):
        flash("Ce nom d'utilisateur est déjà pris.", "error")
        return redirect(url_for('routes.profile', username=user['username']))

    if 'profile_pic' in request.files:
        file = request.files['profile_pic']
        if file and allowed_file(file.filename):
            if user.get('profile_pic_url'):
                old_pic = os.path.join(UPLOAD_FOLDER, os.path.basename(user['profile_pic_url']))
                if os.path.exists(old_pic):
                    os.remove(old_pic)
            filename = secure_filename(f"{current_user_id}_{file.filename}")
            file.save(os.path.join(UPLOAD_FOLDER, filename))
            user['profile_pic_url'] = f"/uploads/profile_pics/{filename}"

    if new_username != user['username']:
        for t in tweets:
            if t['user_id'] == current_user_id:
                t['username'] = new_username
        write_tweets(tweets)

    user['username'] = new_username
    user['bio'] = new_bio
    write_users(users)
    session['username'] = new_username

    flash("Votre profil a été mis à jour !", "success")
    return redirect(url_for('routes.profile', username=new_username))

# ------------------- UPLOADS -------------------
@routes.route('/uploads/profile_pics/<filename>')
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)
