from pathlib import Path
import os, sqlite3, secrets
from flask import Flask, request, session, redirect, render_template, send_from_directory, abort, jsonify
from werkzeug.utils import secure_filename

ROOT=Path(__file__).resolve().parents[1]
LIB=Path(os.getenv("MASH_LIBRARY", ROOT/"library")); LIB.mkdir(parents=True,exist_ok=True)
DB=Path(os.getenv("MASH_DB", ROOT/"library.db"))
app=Flask(__name__); app.secret_key=os.getenv("MASH_SECRET", secrets.token_hex(32))
PASSWORD=os.getenv("MASH_PASSWORD", "change-me")
UPLOAD_TOKEN=os.getenv("MASH_UPLOAD_TOKEN", "change-me-too")

def db():
    c=sqlite3.connect(DB); c.row_factory=sqlite3.Row
    c.execute("CREATE TABLE IF NOT EXISTS tracks(id INTEGER PRIMARY KEY,title TEXT,artist TEXT,filename TEXT,created DATETIME DEFAULT CURRENT_TIMESTAMP)")
    return c

def authed(): return bool(session.get("ok"))

@app.route("/login",methods=["GET","POST"])
def login():
    if request.method=="POST" and secrets.compare_digest(request.form.get("password",""),PASSWORD): session["ok"]=True; return redirect("/")
    return render_template("login.html")

@app.get("/")
def index():
    if not authed(): return redirect("/login")
    c=db(); rows=c.execute("SELECT * FROM tracks ORDER BY created DESC").fetchall(); c.close()
    return render_template("library.html",tracks=rows)

@app.get("/track/<int:tid>/audio")
def audio(tid):
    if not authed(): return redirect("/login")
    c=db(); row=c.execute("SELECT * FROM tracks WHERE id=?",(tid,)).fetchone(); c.close()
    if not row: abort(404)
    return send_from_directory(LIB,row["filename"],as_attachment=True,download_name=row["filename"])

@app.post("/api/tracks")
def upload():
    if not secrets.compare_digest(request.headers.get("Authorization",""),f"Bearer {UPLOAD_TOKEN}"): abort(401)
    f=request.files.get("audio"); title=request.form.get("title","").strip(); artist=request.form.get("artist","").strip()
    if not f or not title: abort(400)
    name=secure_filename(f.filename or title+".mp3"); f.save(LIB/name)
    c=db(); cur=c.execute("INSERT INTO tracks(title,artist,filename) VALUES(?,?,?)",(title,artist,name)); c.commit(); tid=cur.lastrowid; c.close()
    return jsonify(id=tid,path=f"/track/{tid}/audio")

if __name__=="__main__": app.run("127.0.0.1",8000)
