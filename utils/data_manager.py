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
    write_tweets(tweets)

