from flask import Flask
from .database import init_files
from .routes import routes

def create_app():
    app = Flask(__name__, template_folder='../frontend/templates', static_folder='../frontend/static')
    app.secret_key = 'votre_cle_secrete'
    
    init_files()
    app.register_blueprint(routes)
    
    return app
