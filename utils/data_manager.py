import json
import os

# Le dossier data est à la racine du projet
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data'))
USERS_FILE = os.path.join(BASE_DIR, 'users.json')
TWEETS_FILE = os.path.join(BASE_DIR, 'tweets.json')

def init_files():
    """Crée le dossier 'data' et les fichiers JSON seulement s'ils n'existent pas."""
    if not os.path.exists(BASE_DIR):
        os.makedirs(BASE_DIR)
        print(f"Dossier {BASE_DIR} créé.")

    for file in [USERS_FILE, TWEETS_FILE]:
        if not os.path.exists(file):
            with open(file, 'w') as f:
                json.dump([], f, indent=4)
            print(f"Fichier {file} créé avec une liste vide.")
        else:
            print(f"Fichier {file} existe déjà → aucune modification.")

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

def ensure_likes_field():
    """Ajoute le champ 'likes' aux tweets existants si absent."""
    tweets = read_tweets()
    modified = False
    for tweet in tweets:
        if 'likes' not in tweet:
            tweet['likes'] = []
            modified = True
            print(f"Champ 'likes' ajouté pour le tweet id={tweet.get('id')}")
    if modified:
        write_tweets(tweets)
        print("Tweets mis à jour avec le champ 'likes'.")


def follow_user(follower_id, followed_id):
    """
    Ajoute un abonnement : follower_id suit followed_id.
    Retourne True si la mise à jour a réussi, False sinon.
    """
    users = read_users()
    follower = next((u for u in users if u['id'] == follower_id), None)
    followed = next((u for u in users if u['id'] == followed_id), None)
    if not follower or not followed:
        print("Erreur : utilisateur non trouvé.")
        return False
    if followed_id not in follower['following']:
        follower['following'].append(followed_id)
    if follower_id not in followed['followers']:
        followed['followers'].append(follower_id)
    write_users(users)
    print(f"{follower_id} suit maintenant {followed_id}.")
    return True

    # Initialise les listes si elles n'existent pas
def ensure_follow_fields():
    """
    Ajoute les champs 'follower' et 'following' à tous les utilisateurs
    s'ils n'existent pas.
    """
    users = read_users()
    modified = False
    for user in users:
        if 'followers' not in user:
            user['followers'] = []
            modified = True
        if 'following' not in user:
            user['following'] = []
            modified = True
    if modified:
        write_users(users)
        print("Champs 'followers' et 'following' ajoutés aux utilisateurs.")
    else:
        print("Tous les utilisateurs ont déjà les champs 'followers' et 'following'.")

    write_users(users)
    return True

def unfollow_user(follower_id, followed_id):
    """
    Supprime un abonnement : follower_id ne suit plus followed_id.
    Retourne True si la mise à jour a réussi, False sinon.
    """
    users = read_users()
    follower = next((u for u in users if u['id'] == follower_id), None)
    followed = next((u for u in users if u['id'] == followed_id), None)
    if not follower or not followed:
        print("Erreur : utilisateur non trouvé.")
        return False
    if followed_id in follower['following']:
        follower['following'].remove(followed_id)
    if follower_id in followed['followers']:
        followed['followers'].remove(follower_id)
    write_users(users)
    print(f"{follower_id} ne suit plus {followed_id}.")
    return True

    write_users(users, USER_JSON_PATH)
    return True

def ensure_comments_field():
    tweets = read_tweets()
    for tweet in tweets:
        if 'comments' not in tweet:
            tweet['comments'] = []
        else:
            # Ajoute un champ 'likes' à chaque commentaire existant
            for comment in tweet['comments']:
                if 'likes' not in comment:
                    comment['likes'] = []
    write_tweets(tweets)

import json
from datetime import datetime

def retweet_user(tweet_id: str, user_id: str, db_path: str = "user.json"):
    """Ajoute un retweet à la base de données."""
    with open(db_path, "r+") as f:
        data = json.load(f)
        for user in data["users"]:
            if user["id"] == user_id:
                # Vérifie si le tweet original existe
                original_tweet = None
                for u in data["users"]:
                    for tweet in u["tweets"]:
                        if tweet["id"] == tweet_id:
                            original_tweet = tweet
                            break
                if not original_tweet:
                    raise ValueError("Tweet original introuvable.")

                # Crée le retweet
                retweet = {
                    "id": f"retweet_{len(user['retweets'])+1}",
                    "original_tweet_id": tweet_id,
                    "author": original_tweet["author"],
                    "date": datetime.now().strftime("%Y-%m-%d")
                }
                user["retweets"].append(retweet)
                f.seek(0)
                json.dump(data, f, indent=2)
                return retweet
    raise ValueError("Utilisateur introuvable.")

def ensure_retweets_field():
    tweets = read_tweets()
    for tweet in tweets:
        if 'retweets' not in tweet:
            tweet['retweets'] = []
    write_tweets(tweets)


NOTIF_FILE = os.path.join(os.getcwd(), "backend", "data", "notifications.json")

def read_notifications():
    import json
    if not os.path.exists(NOTIF_FILE):
        return []
    with open(NOTIF_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def write_notifications(notifications):
    import json
    # Crée le dossier si nécessaire
    os.makedirs(os.path.dirname(NOTIF_FILE), exist_ok=True)
    with open(NOTIF_FILE, "w", encoding="utf-8") as f:
        json.dump(notifications, f, ensure_ascii=False, indent=4)

def add_notification(to_user_id, from_user_id, notif_type, tweet_id, content=None):
    from datetime import datetime

    notifications = read_notifications()

    notifications.append({
        "to_user_id": to_user_id,
        "from_user_id": from_user_id,
        "type": notif_type,  # "like" ou "comment"
        "tweet_id": tweet_id,
        "content": content,
        "seen": False,
        "created_at": datetime.now().isoformat()
    })

    
    write_notifications(notifications)
