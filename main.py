import os
import json
from functools import wraps
from dotenv import load_dotenv
from flask import Flask, render_template, session, redirect, url_for, request
from werkzeug.security import generate_password_hash, check_password_hash
from wakeonlan import send_magic_packet
from waitress import serve


load_dotenv()
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

mac_address = os.getenv("TARGET_MAC")

USERS_FILE = os.path.join(os.path.dirname(__file__), "users.json")


def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE) as f:
            return json.load(f)
    return {}


def save_users(users_dict):
    with open(USERS_FILE, "w") as f:
        json.dump(users_dict, f, indent=2)
    os.chmod(USERS_FILE, 0o600)


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "username" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated


@app.route('/setup', methods=['GET', 'POST'])
def setup():
    if load_users():
        return redirect(url_for("login"))

    error = None
    if request.method == 'POST':
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm", "")
        if not username or not password:
            error = "Username and password are required."
        elif password != confirm:
            error = "Passwords do not match."
        else:
            save_users({username: generate_password_hash(password, method="scrypt", salt_length=16)})
            session["username"] = username
            return redirect(url_for("index"))

    return render_template("setup.html", error=error)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if not load_users():
        return redirect(url_for("setup"))
    if "username" in session:
        return redirect(url_for("index"))

    error = None
    if request.method == 'POST':
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        users = load_users()
        if username in users and check_password_hash(users[username], password):
            session["username"] = username
            return redirect(url_for("index"))
        error = "Invalid username or password."

    return render_template("login.html", error=error)


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route('/')
@login_required
def index():
    return render_template("index.html", user=session["username"])


@app.route('/wake', methods=['POST'])
@login_required
def wake_device():
    if not mac_address:
        return render_template("wake_result.html", success=False)
    send_magic_packet(mac_address)
    return render_template("wake_result.html", success=True)


if __name__ == '__main__':
    host_ip = os.getenv("HOST_IP", "127.0.0.1")
    port = int(os.getenv("PORT", 5000))

    print(f"Server is running on http://{host_ip}:{port}")

    serve(app, host=host_ip, port=port)
