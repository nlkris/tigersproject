from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify, send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from utils.data_manager import read_users, write_users, read_tweets, write_tweets, init_files, ensure_likes_field, ensure_follow_fields, ensure_comments_field, ensure_retweets_field, add_notification, read_notifications,write_notifications
from datetime import datetime
import os

routes = Blueprint('routes', __name__)

UPLOAD_FOLDER = os.path.join(os.getcwd(), "backend", "uploads", "profile_pics")
TWEET_UPLOAD_FOLDER = os.path.join(os.getcwd(), "backend", "uploads", "tweet_images")
os.makedirs(TWEET_UPLOAD_FOLDER, exist_ok=True)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Initialisation des fichiers
init_files()
ensure_likes_field()
ensure_follow_fields()
ensure_comments_field()
ensure_retweets_field()

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

# ------------------- ✨ RECHERCHE D'UTILISATEURS -------------------
@routes.route('/search', methods=['GET'])
def search():
    if 'user_id' not in session:
        return redirect(url_for('routes.login'))

    users = read_users()
    query = request.args.get("q", "").strip()

    matched_users = []
    if query:
        matched_users = [
            u for u in users
            if query.lower() in u['username'].lower()
        ]

    return render_template(
        'search.html',
        query=query,
        matched_users=matched_users
    )

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
        images = request.files.getlist('images')

        image_urls = []

        # Handle multiple image uploads
        for img in images:
            if img and allowed_file(img.filename):
                filename = secure_filename(f"{current_user_id}_{datetime.now().timestamp()}_{img.filename}")
                img.save(os.path.join(TWEET_UPLOAD_FOLDER, filename))
                image_urls.append(f"/uploads/tweet_images/{filename}")

        # Require at least text or images
        if content or image_urls:
            new_tweet = {
                'id': len(tweets) + 1,
                'user_id': current_user_id,
                'username': session['username'],
                'content': content,
                'image_urls': image_urls,   # <--- HERE: A LIST
                'likes': [],
                'created_at': datetime.now().isoformat()
            }
            tweets.append(new_tweet)
            write_tweets(tweets)

            flash("Votre tweet a été publié !", "success")
            return redirect(url_for('routes.feed'))

        flash("Votre tweet doit contenir un texte ou une image.", "error")
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
                # ✅ Ajouter notif si ce n'est pas son propre tweet
                add_notification(tweet['user_id'], user_id, "like", tweet_id)
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

    current_user = next((u for u in users if u['id'] == session.get('user_id')), None)
    is_current_user = current_user['id'] == profile_user['id']
    is_following = profile_user['id'] in current_user.get('following', []) if current_user else False

    # ----------- Tweets normaux de l'utilisateur -----------
    user_tweets = [t for t in tweets if t['user_id'] == profile_user['id']]

    # ----------- Retweets faits par l'utilisateur -----------
    # ----------- Retweets faits par l'utilisateur -----------
    retweeted_tweets = []
    for tweet in tweets:
        if profile_user['id'] in tweet.get('retweets', []):
            rt_copy = tweet.copy()
            rt_copy['is_retweet'] = True
            rt_copy['retweeted_by'] = profile_user['username']
            retweeted_tweets.append(rt_copy)


    # Fusion tweets + retweets
    all_tweets = user_tweets + retweeted_tweets

    # Tri par date (les retweets apparaissent aussi)
    all_tweets.sort(key=lambda t: t.get('created_at', ''), reverse=True)

    # Ajout des infos manquantes
    for post in all_tweets:
        post.setdefault('likes', [])
        post['liked'] = session['user_id'] in post['likes']

        # Récupération de l'auteur réel du tweet
        tweet_user = next((u for u in users if u['id'] == post['user_id']), None)
        if tweet_user:
            post['username'] = tweet_user['username']
            post['profile_pic_url'] = tweet_user.get('profile_pic_url') or url_for('static', filename='default-avatar.png')
        else:
            post['username'] = "Utilisateur"
            post['profile_pic_url'] = url_for('static', filename='default-avatar.png')

    followers_list = [u for u in users if u['id'] in profile_user.get('followers', [])]
    following_list = [u for u in users if u['id'] in profile_user.get('following', [])]

    return render_template(
        'profile.html',
        profile_user=profile_user,
        user_tweets=all_tweets,
        is_current_user=is_current_user,
        is_following=is_following,
        followers_list=followers_list,
        following_list=following_list
    )

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

        # --- ENSURE username AND profile_pic_url ARE PRESENT ---
        tweet_user = next((u for u in users if u['id'] == post['user_id']), None)
        if tweet_user:
            post['username'] = tweet_user['username']
            # Use uploaded file if exists, else fallback to default
            if tweet_user.get('profile_pic_url'):
                post['profile_pic_url'] = tweet_user['profile_pic_url']
            else:
                post['profile_pic_url'] = url_for('static', filename='default-avatar.png')
        else:
            post['username'] = 'Utilisateur'
            post['profile_pic_url'] = url_for('static', filename='default-avatar.png')

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
            filename = secure_filename(f"{current_user_id}_{file.filename}")
            file.save(os.path.join(UPLOAD_FOLDER, filename))
            user['profile_pic_url'] = url_for('routes.uploaded_file', filename=filename)

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

@routes.route('/uploads/tweet_images/<filename>')
def uploaded_tweet_image(filename):
    return send_from_directory(TWEET_UPLOAD_FOLDER, filename)

#-------------------comments ---------------------
@routes.route('/comment/<int:tweet_id>', methods=['POST'])
def comment_tweet(tweet_id):
    if 'user_id' not in session:
        return jsonify({"success": False, "message": "Non connecté"}), 401
    tweets = read_tweets()
    users = read_users()
    current_user_id = session['user_id']
    current_user = next((u for u in users if u['id'] == current_user_id), None)
    if not current_user:
        return jsonify({"success": False, "message": "Utilisateur introuvable"}), 404
    content = request.form.get('content', '').strip()
    if not content:
        return jsonify({"success": False, "message": "Le commentaire ne peut pas être vide"}), 400
    for tweet in tweets:
        if tweet['id'] == tweet_id:
            tweet.setdefault('comments', [])
            new_comment = {
                'user_id': current_user_id,
                'username': current_user['username'],
                'content': content,
                'created_at': datetime.now().isoformat()
            }
            tweet['comments'].append(new_comment)
            # ✅ Ajouter notification si ce n'est pas son propre tweet
            if tweet['user_id'] != current_user_id:
                add_notification(tweet['user_id'], current_user_id, "comment", tweet_id)

            write_tweets(tweets)
            return jsonify({
                "success": True,
                "comment": new_comment,
                "comment_count": len(tweet['comments'])
            })
    return jsonify({"success": False, "message": "Tweet introuvable"}), 404

@routes.route('/comments/<int:tweet_id>', methods=['GET'])
def get_comments(tweet_id):
    tweets = read_tweets()
    tweet = next((t for t in tweets if t['id'] == tweet_id), None)
    if not tweet or 'comments' not in tweet:
        return jsonify({"success": False, "message": "Tweet ou commentaires introuvables"}), 404
    return jsonify({"success": True, "comments": tweet['comments']})

#------------------- like com----------------------------------
@routes.route('/like_comment/<int:tweet_id>/<int:comment_index>', methods=['POST'])
def like_comment(tweet_id, comment_index):
    if 'user_id' not in session:
        return jsonify({"success": False, "message": "Non connecté"}), 401

    tweets = read_tweets()
    user_id = session['user_id']

    tweet = next((t for t in tweets if t['id'] == tweet_id), None)
    if not tweet:
        return jsonify({"success": False, "message": "Tweet introuvable"}), 404

    if 'comments' not in tweet or not tweet['comments']:
        return jsonify({"success": False, "message": "Aucun commentaire trouvé pour ce tweet"}), 404

    if comment_index < 0 or comment_index >= len(tweet['comments']):
        return jsonify({"success": False, "message": "Index de commentaire invalide"}), 404

    comment = tweet['comments'][comment_index]
    comment.setdefault('likes', [])

    if user_id in comment['likes']:
        comment['likes'].remove(user_id)
        liked = False
    else:
        comment['likes'].append(user_id)
        liked = True

    write_tweets(tweets)

    return jsonify({
        "success": True,
        "liked": liked,
        "like_count": len(comment['likes'])
    })
#------------------- RETWEET ---------------------
@routes.route('/retweet/<int:tweet_id>', methods=['POST'])
def retweet(tweet_id):
    if 'user_id' not in session:
        return jsonify({"success": False, "error": "Utilisateur non connecté"}), 403

    user_id = session['user_id']
    tweets = read_tweets()

    # Trouver tweet
    tweet = next((t for t in tweets if t['id'] == tweet_id), None)
    if not tweet:
        return jsonify({"success": False, "error": "Tweet non trouvé"}), 404

    # Assurer que le champ existe
    tweet.setdefault("retweets", [])

    # Toggle retweet
    if user_id in tweet["retweets"]:
        tweet["retweets"].remove(user_id)
    else:
        tweet["retweets"].append(user_id)

    # Sauvegarder
    write_tweets(tweets)

    # Réponse envoyée au front
    return jsonify({
        "success": True,
        "is_retweeted": user_id in tweet["retweets"],
        "retweet_count": len(tweet["retweets"])
    })
#-------------------com de comment----------------------------------
# Répondre à un commentaire
@routes.route('/reply_comment/<int:tweet_id>/<int:comment_index>', methods=['POST'])
def reply_comment(tweet_id, comment_index):
    if 'user_id' not in session:
        return jsonify({"success": False, "message": "Non connecté"}), 401

    tweets = read_tweets()
    user_id = session['user_id']
    user = next((u for u in read_users() if u['id'] == user_id), None)
    if not user:
        return jsonify({"success": False, "message": "Utilisateur introuvable"}), 404

    tweet = next((t for t in tweets if t['id'] == tweet_id), None)
    if not tweet or 'comments' not in tweet or comment_index >= len(tweet['comments']):
        return jsonify({"success": False, "message": "Commentaire introuvable"}), 404

    data = request.get_json()
    content = data.get('content', '').strip()
    if not content:
        return jsonify({"success": False, "message": "Le contenu est vide"}), 400

    tweet['comments'][comment_index].setdefault('replies', [])
    tweet['comments'][comment_index]['replies'].append({
        'user_id': user_id,
        'username': user['username'],
        'content': content,
        'created_at': datetime.now().isoformat()
    })

    write_tweets(tweets)
    return jsonify({"success": True})

# ------------------- NOTIFICATIONS -------------------
@routes.route('/notifications')
def notifications():
    if 'user_id' not in session:
        return redirect(url_for('routes.login'))

    user_id = session['user_id']
    notifications = read_notifications()
    # Filtrer celles destinées à l'utilisateur
    user_notifs = [n for n in notifications if n['to_user_id'] == user_id]

    # Ajouter le username de l'auteur de chaque notif
    users = read_users()
    for n in user_notifs:
        from_user = next((u for u in users if u['id'] == n['from_user_id']), None)
        n['from_user_username'] = from_user['username'] if from_user else "Utilisateur inconnu"
    # Tu peux les trier par date décroissante
    user_notifs.sort(key=lambda x: x['created_at'], reverse=True)
    users = read_users()
    current_user = next((u for u in users if u['id'] == session['user_id']), None)
    if not current_user:
        return redirect(url_for('routes.login'))

    return render_template("notifications.html", notifications=user_notifs, current_user=current_user)









   

