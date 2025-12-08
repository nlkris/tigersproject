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

    query = request.args.get("q", "").strip()
    
    if query:
        users = read_users()
        matched_user = next((u for u in users if query.lower() in u['username'].lower()), None)
        
        if matched_user:
            # Redirect directly to profile instead of search page
            return redirect(url_for('routes.profile', username=matched_user['username']))
    
    # If no match or no query, go to feed
    return redirect(url_for('routes.feed'))

@routes.route('/search_live')
def search_live():
    """Return JSON for live search suggestions."""
    if 'user_id' not in session:
        return jsonify([])
    
    query = request.args.get('q', '').lower().strip()
    if not query:
        return jsonify([])
    
    users = read_users()
    # Exclude current user from results
    current_user_id = session['user_id']
    
    matched = []
    for user in users:
        if user['id'] != current_user_id and query in user['username'].lower():
            matched.append({
                'id': user['id'],
                'username': user['username'],
                'profile_pic_url': user.get('profile_pic_url')
            })
    
    return jsonify(matched[:10])  # Limit to 10 results

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
                'image_urls': image_urls,
                'likes': [],
                'created_at': datetime.utcnow().isoformat() + 'Z',  # ← FIXED
                'comments': [],  # ← ADD THIS
                'retweets': []   # ← ADD THIS
            }
            tweets.append(new_tweet)
            write_tweets(tweets)

            flash("Votre tweet a été publié !", "success")
            return redirect(url_for('routes.feed'))

        flash("Votre tweet doit contenir un texte ou une image.", "error")
        return redirect(url_for('routes.feed'))

    # First, ensure all tweets have created_at
    for tweet in tweets:
        if 'created_at' not in tweet:
            tweet['created_at'] = '1970-01-01T00:00:00Z'  # Very old date
    
     # Now sort ALL tweets by date
    tweets.sort(key=lambda t: t.get('created_at', '1970-01-01T00:00:00Z'), reverse=True)

    # Add liked field
    for post in tweets:
        post.setdefault('likes', [])
        post['liked'] = current_user_id in post['likes']
   
    # Filter tweets
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
        # ✅ Ajouter notification de follow
        add_notification(target_user['id'], current_user_id, "follow", None, None)

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
    retweeted_tweets = []
    for tweet in tweets:
        retweets_list = tweet.get('retweets', [])
    
        # Check if this user has retweeted this tweet (supporting both old and new format)
        has_retweeted = False
        retweet_timestamp = None
        
        for retweet in retweets_list:
            if isinstance(retweet, dict):
                # New format: {"user_id": X, "retweeted_at": "timestamp"}
                if retweet.get('user_id') == profile_user['id']:
                    has_retweeted = True
                    retweet_timestamp = retweet.get('retweeted_at')
                    break
            elif isinstance(retweet, int):
                # Old format: just user_id
                if retweet == profile_user['id']:
                    has_retweeted = True
                    # For old retweets, use the tweet's created_at as fallback
                    retweet_timestamp = tweet.get('created_at')
                    break
        
        if has_retweeted:
            rt_copy = tweet.copy()
            rt_copy['is_retweet'] = True
            rt_copy['retweeted_by'] = profile_user['username']
            rt_copy['retweeted_at'] = retweet_timestamp  # Store the retweet timestamp
            retweeted_tweets.append(rt_copy)


    # Fusion tweets + retweets
    all_tweets = user_tweets + retweeted_tweets

    # Tri par date (les retweets apparaissent aussi)
    # Sort by retweet timestamp if it's a retweet, else by created_at
    def get_sort_time(tweet):
        if tweet.get('is_retweet') and tweet.get('retweeted_at'):
            return tweet['retweeted_at']
        return tweet.get('created_at', '')

    def get_sort_time(tweet):
        if tweet.get('is_retweet') and tweet.get('retweeted_at'):
            ts = tweet['retweeted_at']
        else:
            ts = tweet.get('created_at', '')
        
        if not ts:
            return '1970-01-01T00:00:00Z'
        return ts
    
    all_tweets.sort(key=get_sort_time, reverse=True)

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
            add_notification(tweet['user_id'], current_user_id, "comment", tweet_id, content)

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

    # Assurer que le champ existe avec la nouvelle structure
    tweet.setdefault("retweets", [])
    
    # Convertir l'ancienne structure (liste d'IDs) vers la nouvelle structure (liste d'objets)
    if tweet["retweets"] and isinstance(tweet["retweets"][0], int):
        # Conversion avec un timestamp par défaut (date actuelle)
        # [user_id1, user_id2] -> [{"user_id": user_id1, "retweeted_at": "timestamp"}, ...]
        tweet["retweets"] = [{"user_id": uid, "retweeted_at": datetime.utcnow().isoformat()} for uid in tweet["retweets"]]

    # Chercher si l'utilisateur a déjà retweeté
    existing_retweet = next((rt for rt in tweet["retweets"] if rt["user_id"] == user_id), None)
    
    if existing_retweet:
        # Supprimer le retweet
        tweet["retweets"] = [rt for rt in tweet["retweets"] if rt["user_id"] != user_id]
        is_retweeted = False
    else:
        # Ajouter un nouveau retweet avec timestamp
        from datetime import datetime
        new_retweet = {
            "user_id": user_id,
            "retweeted_at": datetime.utcnow().isoformat()
        }
        tweet["retweets"].append(new_retweet)
        is_retweeted = True
        # ✅ Ajouter notification si ce n'est pas son propre tweet
        add_notification(tweet['user_id'], user_id, "retweet", tweet_id)

    # Sauvegarder
    write_tweets(tweets)

    # Réponse envoyée au front
    return jsonify({
        "success": True,
        "is_retweeted": is_retweeted,
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
    users = read_users()
    user = next((u for u in users if u['id'] == user_id), None)
    if not user:
        return jsonify({"success": False, "message": "Utilisateur introuvable"}), 404

    tweet = next((t for t in tweets if t['id'] == tweet_id), None)
    if not tweet or 'comments' not in tweet or comment_index >= len(tweet['comments']):
        return jsonify({"success": False, "message": "Commentaire introuvable"}), 404

    data = request.get_json()
    if not data:
        return jsonify({"success": False, "message": "Données JSON manquantes"}), 400
        
    content = data.get('content', '').strip()
    if not content:
        return jsonify({"success": False, "message": "Le contenu est vide"}), 400

    # Ensure replies list exists
    if 'replies' not in tweet['comments'][comment_index]:
        tweet['comments'][comment_index]['replies'] = []
    
    # Add the reply
    tweet['comments'][comment_index]['replies'].append({
        'user_id': user_id,
        'username': user['username'],
        'content': content,
        'created_at': datetime.now().isoformat()
    })
    
    # ✅ NOTIFICATION 1: Notify the TWEET AUTHOR
    tweet_author_id = tweet['user_id']
    
    # Only notify tweet author if it's not the same person replying
    if tweet_author_id != user_id:
        # Get the original comment that's being replied to
        original_comment = tweet['comments'][comment_index]
        original_comment_content = original_comment.get('content', '')
        
        # Truncate if too long
        if len(original_comment_content) > 50:
            original_comment_content = original_comment_content[:47] + "..."
        
        # Format: Someone replied to a comment on your tweet
        notification_content = f"REPLY_ON_TWEET:'{original_comment_content}'|REPLY:'{content}'"
        
        add_notification(tweet_author_id, user_id, "reply_on_tweet", tweet_id, notification_content)
    
    # ✅ NOTIFICATION 2: Notify the COMMENT AUTHOR (original code)
    original_comment = tweet['comments'][comment_index]
    original_comment_author_id = original_comment.get('user_id')
    
    # Only notify comment author if replying to someone else's comment
    if original_comment_author_id != user_id:
        # Get the original comment content
        original_comment_content = original_comment.get('content', '')
        
        # Truncate if too long
        if len(original_comment_content) > 50:
            original_comment_content = original_comment_content[:47] + "..."
        
        # Create formatted content
        notification_content = f"REPLY_TO:'{original_comment_content}'|REPLY:'{content}'"
        
        add_notification(original_comment_author_id, user_id, "reply", tweet_id, notification_content)
    
    write_tweets(tweets)
    return jsonify({"success": True, "message": "Réponse ajoutée"})

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

@routes.route('/api/current_user')
def get_current_user():
    if 'user_id' not in session:
        return jsonify({}), 401
    
    users = read_users()
    user = next((u for u in users if u['id'] == session['user_id']), None)
    
    if user:
        return jsonify({
            'id': user['id'],
            'username': user['username'],
            'following': user.get('following', [])
        })
    
    return jsonify({}), 404

# ------------------- MIGRATE RETWEETS (one-time) -------------------
@routes.route('/migrate-retweets')
def migrate_retweets():
    """Migrate all old retweets (list of IDs) to new format (list of objects with timestamp)"""
    if 'user_id' not in session:
        return redirect(url_for('routes.login'))
    
    tweets = read_tweets()
    updated_count = 0
    
    for tweet in tweets:
        retweets = tweet.get('retweets', [])
        if retweets and isinstance(retweets[0], int):
            # Convert old format to new format
            # Use the tweet's created_at as the retweet timestamp (best guess)
            tweet['retweets'] = [
                {
                    "user_id": uid, 
                    "retweeted_at": tweet.get('created_at', datetime.utcnow().isoformat())
                } 
                for uid in retweets
            ]
            updated_count += 1
    
    if updated_count > 0:
        write_tweets(tweets)
        return f"Migrated {updated_count} tweets with old retweet format to new format."
    else:
        return "No tweets needed migration."







   

