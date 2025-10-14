import json
import os

# Chemins vers les fichiers JSON
USER_JSON_PATH = 'users.json'
TWEETS_JSON_PATH = 'tweets.json'

def load_data(file_path):
    """Charge les données depuis un fichier JSON."""
    if not os.path.exists(file_path):
        return []
    with open(file_path, 'r') as f:
        return json.load(f)

def save_data(data, file_path):
    """Sauvegarde les données dans un fichier JSON."""
    with open(file_path, 'w') as f:
        json.dump(data, f, indent=2)

# Gestion des utilisateurs
def get_all_users():
    return load_data(USER_JSON_PATH)

def get_user_by_id(user_id):
    users = load_data(USER_JSON_PATH)
    for user in users:
        if user['id'] == user_id:
            return user
    return None

# Gestion des tweets
def get_tweets_by_user(user_id):
    tweets = load_data(TWEETS_JSON_PATH)
    return [tweet for tweet in tweets if tweet['user_id'] == user_id]


