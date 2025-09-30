from flask import Flask, render_template, request, redirect, session, url_for, flash
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
import webbrowser
import threading

app = Flask(__name__)
app.secret_key = 'ton_secret_key'

DB = 'twinsa.db'

# --- Initialisation de la base de données ---
def init_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            email TEXT UNIQUE,
            password TEXT
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            content TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# --- Routes ---
@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/signup', methods=['GET','POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username'].strip()
        email = request.form['email'].strip()
        password = request.form['password'].strip()
        if not username or not email or not password:
            flash("Tous les champs sont obligatoires.", "error")
            return redirect(url_for('signup'))
        hashed = generate_password_hash(password)
        try:
            conn = sqlite3.connect(DB)
            c = conn.cursor()
            c.execute("INSERT INTO users (username,email,password) VALUES (?,?,?)",
                      (username,email,hashed))
            conn.commit()
            user_id = c.lastrowid  # ID du nouvel utilisateur
            conn.close()
            # Création de la session pour l’utilisateur
            session['user_id'] = user_id
            session['username'] = username
            # Redirection directe vers le feed
            return redirect(url_for('feed'))
        except sqlite3.IntegrityError:
            flash("Nom d'utilisateur ou email déjà utilisé.", "error")
            return redirect(url_for('signup'))
    return render_template('signup.html')

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method=='POST':
        email = request.form['email'].strip()
        password = request.form['password'].strip()
        conn = sqlite3.connect(DB)
        c = conn.cursor()
        c.execute("SELECT id,password,username FROM users WHERE email=?",(email,))
        user = c.fetchone()
        conn.close()
        if user and check_password_hash(user[1], password):
            session['user_id'] = user[0]
            session['username'] = user[2]
            return redirect(url_for('feed'))
        else:
            flash("Email ou mot de passe invalide.", "error")
            return redirect(url_for('login'))
    return render_template('login.html')

@app.route('/feed', methods=['GET','POST'])
def feed():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    if request.method=='POST':
        content = request.form['content'].strip()
        if content:
            c.execute("INSERT INTO posts (user_id,content) VALUES (?,?)",
                      (session['user_id'],content))
            conn.commit()
    c.execute("""
        SELECT posts.id, posts.content, posts.created_at, users.username 
        FROM posts JOIN users ON posts.user_id = users.id
        ORDER BY posts.created_at DESC
    """)
    posts = c.fetchall()
    conn.close()
    return render_template('feed.html', posts=posts, username=session['username'])

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# --- Lancer le serveur et ouvrir le navigateur automatiquement ---
if __name__ == '__main__':
    def open_browser():
        webbrowser.open_new("http://127.0.0.1:5000/")
    threading.Timer(1, open_browser).start()
    app.run(debug=True)
