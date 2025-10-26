# run.py
import os
from flask import Flask, render_template, request, redirect, url_for, send_from_directory, session, flash
from datetime import datetime
from werkzeug.utils import secure_filename
from PIL import Image
import json
import mimetypes
import qrcode

UPLOAD_FOLDER = "uploads"
THUMB_FOLDER = os.path.join(UPLOAD_FOLDER, "thumbs")
LOG_FILE = "audit_log.json"
ALLOWED_EXT = None
MAX_SIZE_BYTES = 80 * 1024 * 1024
ADMIN_PASS = os.getenv("DARKVAULT_ADMIN_PASS", "hasnain")
SECRET_KEY = os.getenv("DARKVAULT_SECRET", "change-me-1234")

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(THUMB_FOLDER, exist_ok=True)
app = Flask(__name__)
app.secret_key = SECRET_KEY
app.config['MAX_CONTENT_LENGTH'] = MAX_SIZE_BYTES

def log_event(event):
    entry = {"time": datetime.utcnow().isoformat()+"Z", **event}
    data = []
    if os.path.exists(LOG_FILE):
        try:
            with open(LOG_FILE,"r") as f:
                data = json.load(f)
        except Exception:
            data = []
    data.append(entry)
    with open(LOG_FILE,"w") as f:
        json.dump(data, f, indent=2)

def list_recent(n=20):
    items = []
    for fname in os.listdir(UPLOAD_FOLDER):
        full = os.path.join(UPLOAD_FOLDER, fname)
        if os.path.isdir(full): continue
        stat = os.stat(full)
        items.append({
            "name": fname,
            "size": stat.st_size,
            "mtime": stat.st_mtime,
            "mime": mimetypes.guess_type(fname)[0] or "unknown"
        })
    items = sorted(items, key=lambda x: x["mtime"], reverse=True)
    return items[:n]

def make_thumbnail(filepath, thumbpath, maxsize=(240,240)):
    try:
        im = Image.open(filepath)
        im.thumbnail(maxsize)
        im.save(thumbpath, format="PNG")
        return True
    except Exception:
        return False

def is_image(filename):
    mime = mimetypes.guess_type(filename)[0] or ""
    return mime.startswith("image/")

def generate_qr_for_link(link, outpath):
    try:
        img = qrcode.make(link)
        img.save(outpath)
        return True
    except Exception:
        return False

@app.route("/", methods=["GET","POST"])
def index():
    if request.method == "POST":
        f = request.files.get("file")
        if not f or f.filename == "":
            flash("No file selected.", "error")
            return redirect(url_for("index"))
        filename = secure_filename(f.filename)
        if ALLOWED_EXT:
            ext = filename.rsplit(".",1)[-1].lower() if "." in filename else ""
            if ext not in ALLOWED_EXT:
                flash("File type not allowed.", "error")
                return redirect(url_for("index"))
        ts = datetime.now().strftime("%Y%m%d%H%M%S")
        saved_name = f"{ts}_{filename}"
        outpath = os.path.join(UPLOAD_FOLDER, saved_name)
        f.save(outpath)
        if is_image(saved_name):
            thumb_path = os.path.join(THUMB_FOLDER, f"{saved_name}.png")
            make_thumbnail(outpath, thumb_path)
        download_url = url_for("download_file", filename=saved_name, _external=True)
        qr_path = os.path.join(THUMB_FOLDER, f"{saved_name}_qr.png")
        generate_qr_for_link(download_url, qr_path)
        log_event({"action":"upload","file":saved_name, "ip": request.remote_addr, "ua": request.headers.get("User-Agent","")})
        flash(f"Uploaded: {saved_name}", "success")
        return redirect(url_for("index"))
    files = list_recent(30)
    return render_template("index.html", files=files)

@app.route("/uploads/<path:filename>")
def download_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename, as_attachment=True)

@app.route("/thumbs/<path:filename>")
def thumb_file(filename):
    return send_from_directory(THUMB_FOLDER, filename)

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method=="POST":
        pw = request.form.get("password","")
        if pw == ADMIN_PASS:
            session["admin"] = True
            flash("Logged in as admin.", "success")
            return redirect(url_for("admin"))
        else:
            flash("Wrong password.", "error")
            return redirect(url_for("login"))
    return render_template("login.html")

def admin_required(func):
    from functools import wraps
    @wraps(func)
    def wrapper(*a, **k):
        if not session.get("admin"):
            flash("Admin login required.", "error")
            return redirect(url_for("login"))
        return func(*a, **k)
    return wrapper

@app.route("/admin")
@admin_required
def admin():
    files = list_recent(200)
    logs = []
    if os.path.exists(LOG_FILE):
        try:
            with open(LOG_FILE,"r") as f:
                logs = json.load(f)
        except Exception:
            logs = []
    return render_template("admin.html", files=files, logs=logs)

@app.route("/delete/<filename>", methods=["POST"])
@admin_required
def delete_file(filename):
    safe = secure_filename(filename)
    path = os.path.join(UPLOAD_FOLDER, safe)
    if os.path.exists(path):
        os.remove(path)
        t1 = os.path.join(THUMB_FOLDER, f"{safe}.png")
        t2 = os.path.join(THUMB_FOLDER, f"{safe}_qr.png")
        for p in (t1,t2):
            if os.path.exists(p): os.remove(p)
        log_event({"action":"delete","file":safe, "admin_ip": request.remote_addr})
        flash(f"Deleted {safe}", "success")
    else:
        flash("File not found.", "error")
    return redirect(url_for("admin"))

@app.route("/logout")
def logout():
    session.pop("admin", None)
    flash("Logged out.", "info")
    return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
