"""Smart Job Scheduling System (FCFS, SJF, SRTF, Priority, Round Robin) - Flask backend.
Run:  pip install -r requirements.txt   then   python app.py
Open: http://127.0.0.1:5000
"""
import json
import os
import threading

from flask import Flask, jsonify, render_template, request

from scheduler import ALGOS, sample_jobs, schedule

app = Flask(__name__)
DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "jobs.json")
lock = threading.Lock()   # one request writes the file at a time


# ---------- tiny "database": a JSON file you can also open and edit by hand ----------
def sample_db():
    jobs = sample_jobs()
    return {"next_id": len(jobs) + 1, "jobs": jobs}


def load():
    if not os.path.exists(DB_FILE):          # first run: start with the sample jobs
        return sample_db()
    with open(DB_FILE, encoding="utf-8") as f:
        return json.load(f)


def save(db):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(db, f, indent=2)


def clean(data, db):
    """Validate what the browser sent and return a tidy job dict."""
    try:
        arrival = float(data.get("arrival"))
        burst = float(data.get("burst"))
        priority = int(float(data.get("priority")))
    except (TypeError, ValueError):
        raise ValueError("Arrival, burst and priority must be numbers.")
    if arrival < 0:
        raise ValueError("Arrival time must be 0 or more.")
    if burst <= 0:
        raise ValueError("Burst time must be greater than 0.")
    if priority < 1:
        raise ValueError("Priority must be 1 or more.")
    name = str(data.get("name", "")).strip()[:30] or "P" + str(db["next_id"])
    return {"name": name, "arrival": arrival, "burst": burst, "priority": priority}


@app.errorhandler(ValueError)
def bad_input(err):
    return jsonify(error=str(err)), 400


# ---------- pages ----------
@app.get("/")
def home():
    return render_template("index.html", algos=ALGOS)


# ---------- REST API used by the page ----------
@app.get("/api/jobs")
def list_jobs():
    return jsonify(load()["jobs"])


@app.post("/api/jobs")
def add_job():
    with lock:
        db = load()
        job = clean(request.get_json(force=True), db)
        job["id"] = db["next_id"]
        db["next_id"] += 1
        db["jobs"].append(job)
        save(db)
    return jsonify(job), 201


@app.put("/api/jobs/<int:job_id>")
def edit_job(job_id):
    with lock:
        db = load()
        job = next((j for j in db["jobs"] if j["id"] == job_id), None)
        if job is None:
            return jsonify(error="Job not found."), 404
        job.update(clean(request.get_json(force=True), db))
        save(db)
    return jsonify(job)


@app.delete("/api/jobs/<int:job_id>")
def delete_job(job_id):
    with lock:
        db = load()
        db["jobs"] = [j for j in db["jobs"] if j["id"] != job_id]
        save(db)
    return jsonify(ok=True)


@app.post("/api/clear")
def clear_jobs():
    with lock:
        save({"next_id": 1, "jobs": []})
    return jsonify(ok=True)


@app.post("/api/sample")
def load_sample():
    with lock:
        save(sample_db())
    return jsonify(ok=True)


@app.get("/api/schedule")
def make_schedule():
    jobs = load()["jobs"]
    algo = request.args.get("algo", "fcfs")
    algo = algo if algo in ALGOS else "fcfs"
    quantum = max(0.5, request.args.get("quantum", 2, type=float))
    result = schedule(jobs, algo, quantum)
    # run every algorithm so the page can compare them
    result["compare"] = {k: schedule(jobs, k, quantum)["metrics"] for k in ALGOS} if jobs else {}
    return jsonify(result)


if __name__ == "__main__":
    app.run(debug=True)
