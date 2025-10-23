from flask import Flask
from backend.routes import routes
from utils.data_manager import init_files, ensure_likes_field, ensure_follow_fields

app = Flask(__name__)
app.secret_key = 'votre_cle_secrete'

# Enregistrement du blueprint
app.register_blueprint(routes)

# Initialisation des fichiers JSON
init_files()
ensure_likes_field()
ensure_follow_fields()

if __name__ == '__main__':
    app.run(debug=True)
