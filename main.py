import os
import json
from functools import wraps
from dotenv import load_dotenv
from flask import Flask, render_template_string, session, redirect, url_for, request
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
    users = {}
    seed_user = os.getenv("WOL_USERNAME")
    seed_pass = os.getenv("WOL_PASSWORD")
    if seed_user and seed_pass:
        users[seed_user] = generate_password_hash(seed_pass, method="scrypt", salt_length=16)
    save_users(users)
    return users


def save_users(users_dict):
    with open(USERS_FILE, "w") as f:
        json.dump(users_dict, f, indent=2)


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "username" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated


try:
    with open('static/styles.css', 'r') as css_file:
        global_styles = css_file.read()
except FileNotFoundError:
    print("Warning: styles.css not found.")
    global_styles = "body {font-family: Arial, sans-serif; background-color: #f0f8ff; text-align:center;}"


@app.context_processor
def inject_styles():
    return dict(styles=global_styles)


@app.route('/login', methods=['GET', 'POST'])
def login():
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

    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Login</title>
        <style>{{ styles }}</style>
    </head>
    <body>
        <h1>Home Gateway</h1>
        <div class="auth-container">
            <h2>Login</h2>
            {% if error %}
            <p class="error-msg">{{ error }}</p>
            {% endif %}
            <form method="POST">
                <label for="username">Username</label>
                <input type="text" id="username" name="username" required autofocus>
                <label for="password">Password</label>
                <input type="password" id="password" name="password" required>
                <div class="btn-row">
                    <button type="submit" class="btn btn-primary">Login</button>
                    <a href="{{ url_for('register') }}" class="btn btn-secondary">Create Account</a>
                </div>
            </form>
        </div>
    </body>
    </html>
    """
    return render_template_string(html_content, error=error)


@app.route('/register', methods=['GET', 'POST'])
def register():
    error = None
    success = None
    if request.method == 'POST':
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm", "")
        users = load_users()
        if not username or not password:
            error = "Username and password are required."
        elif username in users:
            error = "That username is already taken."
        elif password != confirm:
            error = "Passwords do not match."
        else:
            users[username] = generate_password_hash(password, method="scrypt", salt_length=16)
            save_users(users)
            return redirect(url_for("login"))

    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Create Account</title>
        <style>{{ styles }}</style>
    </head>
    <body>
        <h1>Home Gateway</h1>
        <div class="auth-container">
            <h2>Create Account</h2>
            {% if error %}
            <p class="error-msg">{{ error }}</p>
            {% endif %}
            <form method="POST">
                <label for="username">Username</label>
                <input type="text" id="username" name="username" required autofocus>
                <label for="password">Password</label>
                <input type="password" id="password" name="password" required>
                <label for="confirm">Confirm Password</label>
                <input type="password" id="confirm" name="confirm" required>
                <div class="btn-row">
                    <button type="submit" class="btn btn-primary">Create Account</button>
                    <a href="{{ url_for('login') }}" class="btn btn-secondary">Back to Login</a>
                </div>
            </form>
        </div>
    </body>
    </html>
    """
    return render_template_string(html_content, error=error)


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route('/')
@login_required
def index():
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Home Gateway</title>
        <style>{{ styles }}</style>
    </head>
    <body>
        <h1>Home PC Gateway</h1>
        <p>User Authenticated: {{ user }}</p>
        <p>Target System: Taylor PC</p>
        <form action="/wake" method="POST">
            <button type="submit" style="padding:20px 40px; font-size:50px; cursor:pointer;">
                SEND WAKE-ON-LAN PACKET!
            </button>
        </form>
        <p><a href="{{ url_for('logout') }}">Logout</a></p>
    </body>
    </html>
    """
    return render_template_string(html_content, user=session["username"])


@app.route('/wake', methods=['POST'])
@login_required
def wake_device():
    if not mac_address:
        html_content = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>ERROR</title>
            <style>{{ styles }}</style>
        </head>
        <body>
            <h1>ERROR</h1>
            <p>MAC address not configured. Please set TARGET_MAC in the .env file. <a href='/'>Return Home</a></p>
        </body>
        </html>
        """
        return render_template_string(html_content)
    else:
        send_magic_packet(mac_address)
        html_content = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Success!!!</title>
            <style>{{ styles }}</style>
        </head>
        <body>
            <h1>Success!!!</h1>
            <p>Wake-On-Lan Magic Packet broadcasted. <a href='/'>Return Home</a></p>
        </body>
        </html>
        """
        return render_template_string(html_content)


if __name__ == '__main__':
    host_ip = os.getenv("HOST_IP", "127.0.0.1")
    port = int(os.getenv("PORT", 5000))

    print(f"Server is running on http://{host_ip}:{port}")

    serve(app, host=host_ip, port=port)
