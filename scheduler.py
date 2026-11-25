"""CPU-style job scheduling: FCFS, SJF, SRTF, Priority and Round Robin.

A job is a dict:  {"id": 1, "name": "P1", "arrival": 0, "burst": 8, "priority": 3}
Run this file directly (python scheduler.py) to see every algorithm on the sample jobs.
"""

ALGOS = {
    "fcfs": ("FCFS (First Come, First Served)",
             "Runs jobs in the order they arrive. A running job is never interrupted."),
    "sjf": ("SJF (Shortest Job First)",
            "When the CPU is free, it picks the waiting job with the smallest burst time. Non-preemptive."),
    "srtf": ("SRTF (Shortest Remaining Time First)",
             "Preemptive SJF. If a new job needs less time than what is left of the running job, it takes over the CPU."),
    "priority": ("Priority (non-preemptive)",
                 "When the CPU is free, it picks the waiting job with the highest priority (lowest number)."),
    "rr": ("Round Robin",
           "Each job gets the CPU for one time quantum, then goes to the back of the queue."),
}

SAMPLE = [("P1", 0, 8, 3), ("P2", 1, 4, 1), ("P3", 2, 9, 4), ("P4", 3, 5, 2)]  # name, arrival, burst, priority


def sample_jobs():
    return [{"id": i, "name": n, "arrival": a, "burst": b, "priority": p}
            for i, (n, a, b, p) in enumerate(SAMPLE, 1)]


def schedule(jobs, algo="fcfs", quantum=2):
    """Simulate one CPU. Returns Gantt segments, per-job results and averages."""
    if not jobs:
        return {"segments": [], "rows": [], "metrics": None}

    # work on copies: rem = time still needed, first = first time on the CPU, done = completion time
    P = [dict(j, i=i, rem=j["burst"], first=None, done=None) for i, j in enumerate(jobs)]
    segments = []

    def idle(start, end):
        segments.append({"idle": True, "start": start, "end": end})

    def run(p, start, length):
        """Give the CPU to job p from `start` for `length` time units; return the new time."""
        if p["first"] is None:
            p["first"] = start
        p["rem"] -= length
        end = start + length
        last = segments[-1] if segments else None
        if last and last.get("id") == p["id"] and abs(last["end"] - start) < 1e-9:
            last["end"] = end                       # same job continues: extend its block
        else:
            segments.append({"id": p["id"], "name": p["name"], "index": p["i"], "start": start, "end": end})
        if p["rem"] < 1e-9:
            p["rem"], p["done"] = 0, end
        return end

    t = 0.0
    if algo == "rr":
        queue, seen = [], set()

        def admit(now):                             # move newly arrived jobs into the queue
            new = [p for p in P if p["arrival"] <= now and p["i"] not in seen]
            for p in sorted(new, key=lambda p: (p["arrival"], p["i"])):
                seen.add(p["i"])
                queue.append(p)

        while any(p["rem"] > 0 for p in P):
            admit(t)
            if not queue:                           # CPU idle until the next arrival
                nxt = min(p["arrival"] for p in P if p["i"] not in seen)
                idle(t, nxt)
                t = nxt
                continue
            p = queue.pop(0)
            t = run(p, t, min(p["rem"], quantum))
            admit(t)                                # jobs that arrived meanwhile queue before p
            if p["rem"] > 0:
                queue.append(p)
    else:
        key = {                                     # smaller key = chosen first
            "fcfs": lambda p: (p["arrival"], p["i"]),
            "sjf": lambda p: (p["rem"], p["arrival"], p["i"]),
            "srtf": lambda p: (p["rem"], p["arrival"], p["i"]),
            "priority": lambda p: (p["priority"], p["arrival"], p["i"]),
        }[algo]
        while any(p["rem"] > 0 for p in P):
            ready = [p for p in P if p["arrival"] <= t and p["rem"] > 0]
            if not ready:
                nxt = min(p["arrival"] for p in P if p["rem"] > 0)
                idle(t, nxt)
                t = nxt
                continue
            p = min(ready, key=key)
            length = p["rem"]                       # non-preemptive: run to the end
            if algo == "srtf":                      # preemptive: stop at the next arrival, then choose again
                later = [q["arrival"] for q in P if q["arrival"] > t and q["rem"] > 0]
                if later:
                    length = min(length, min(later) - t)
            t = run(p, t, length)

    r = lambda x: round(x, 2)
    rows = []
    for p in P:
        turnaround = p["done"] - p["arrival"]
        rows.append({"id": p["id"], "name": p["name"], "arrival": p["arrival"], "burst": p["burst"],
                     "completion": r(p["done"]), "turnaround": r(turnaround),
                     "waiting": r(turnaround - p["burst"]), "response": r(p["first"] - p["arrival"])})
    for s in segments:
        s["start"], s["end"] = r(s["start"]), r(s["end"])

    n, total = len(rows), max(x["completion"] for x in rows)
    avg = lambda k: r(sum(x[k] for x in rows) / n)
    metrics = {"avg_waiting": avg("waiting"), "avg_turnaround": avg("turnaround"),
               "avg_response": avg("response"), "total_time": total,
               "cpu_utilization": r(100 * sum(x["burst"] for x in rows) / total),
               "preemptions": sum(1 for s in segments if not s.get("idle")) - n}
    return {"segments": segments, "rows": rows, "metrics": metrics}


if __name__ == "__main__":                          # console demo
    jobs = sample_jobs()
    for key, (title, _) in ALGOS.items():
        res = schedule(jobs, key, quantum=2)
        print(f"\n=== {title} ===")
        gantt = [f"{s['start']:g} [{'Idle' if s.get('idle') else s['name']}]" for s in res["segments"]]
        print("Gantt: " + " ".join(gantt) + f" {res['segments'][-1]['end']:g}")
        print(f"{'Job':<6}{'AT':>4}{'BT':>4}{'CT':>5}{'TAT':>6}{'WT':>5}{'RT':>5}")
        for x in res["rows"]:
            print(f"{x['name']:<6}{x['arrival']:>4g}{x['burst']:>4g}{x['completion']:>5g}"
                  f"{x['turnaround']:>6g}{x['waiting']:>5g}{x['response']:>5g}")
        m = res["metrics"]
        print(f"Average waiting = {m['avg_waiting']}, turnaround = {m['avg_turnaround']}, response = {m['avg_response']}")
