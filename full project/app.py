from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import json, os, datetime
from werkzeug.utils import secure_filename
import face_recognition

app = Flask(__name__)
app.secret_key = "bioface_secret_key"

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
USERS_FILE = "users.json"

# ---------------- HELPER FUNCTIONS ----------------
def load_users():
    if not os.path.exists(USERS_FILE):
        return {}
    with open(USERS_FILE, "r") as f:
        return json.load(f)

def save_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=4)

def can_login(user):
    now = datetime.datetime.now()
    week_start = now - datetime.timedelta(days=now.weekday())  # Monday start
    user_logins = [datetime.datetime.fromisoformat(t) for t in user.get("logins", [])]
    recent_logins = [t for t in user_logins if t >= week_start]
    return len(recent_logins) < 3

# ---------------- ROUTES ----------------
@app.route("/")
def home():
    return redirect(url_for("login_page"))

@app.route("/login")
def login_page():
    return render_template("login.html")

@app.route("/dashboard")
def dashboard_page():
    if "username" not in session:
        return redirect(url_for("login_page"))
    return render_template("dashboard.html", username=session["username"])

@app.route("/api/login", methods=["POST"])
def login_api():
    data = request.json
    username = data.get("username")
    password = data.get("password")
    users = load_users()

    if username not in users:
        return jsonify({"success": False, "message": "User not found."}), 400

    user = users[username]
    if user["password"] != password:
        return jsonify({"success": False, "message": "Incorrect password."}), 400

    if not can_login(user):
        return jsonify({
            "success": False,
            "message": "You have reached your maximum login attempts (3) for this week. Please try again next week."
        }), 403

    user.setdefault("logins", []).append(datetime.datetime.now().isoformat())
    save_users(users)
    session["username"] = username
    return jsonify({"success": True})

@app.route("/api/face-analysis", methods=["POST"])
def face_analysis():
    if "username" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    if "image" not in request.files:
        return jsonify({"error": "No image uploaded"}), 400

    file = request.files["image"]
    filename = secure_filename(file.filename)
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    file.save(filepath)

    try:
        image = face_recognition.load_image_file(filepath)
        face_locations = face_recognition.face_locations(image)
        result = {
            "faces_detected": len(face_locations),
            "analysis": "Potential fever indicators detected" if len(face_locations) else "No face detected"
        }
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login_page"))

# ---------------- DEFAULT USER ----------------
if not os.path.exists(USERS_FILE):
    default_user = {
        "admin": {"password": "bio123", "logins": []}
    }
    save_users(default_user)

if __name__ == "__main__":
    app.run(debug=True)

