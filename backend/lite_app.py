import http.server
import json
import sqlite3
import threading
import time
from datetime import datetime
import urllib.request
import urllib.parse

# Database Setup
def init_db():
    conn = sqlite3.connect('scheduler.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS targets 
                 (id INTEGER PRIMARY KEY, name TEXT, url TEXT, method TEXT, headers TEXT, body TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS schedules 
                 (id INTEGER PRIMARY KEY, target_id INTEGER, name TEXT, type TEXT, value TEXT, status TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS runs 
                 (id INTEGER PRIMARY KEY, schedule_id INTEGER, status TEXT, started_at TEXT, latency_ms REAL)''')
    conn.commit()
    conn.close()

# Scheduler Logic
def scheduler_loop():
    while True:
        try:
            conn = sqlite3.connect('scheduler.db')
            c = conn.cursor()
            c.execute("SELECT s.id, s.target_id, s.type, s.value, s.status, t.url, t.method, t.headers, t.body FROM schedules s JOIN targets t ON s.target_id = t.id WHERE s.status = 'active'")
            active_schedules = c.fetchall()
            conn.close()

            # For simplicity in this lite version, we just run everything that's due
            # In a real app we'd track last_run_at. Here we'll just sleep 10s and run everything for demo.
            for s in active_schedules:
                threading.Thread(target=execute_request, args=(s,)).start()
            
            time.sleep(10) # Run every 10s for demo purposes in this lite version
        except Exception as e:
            print(f"Scheduler error: {e}")
            time.sleep(5)

def execute_request(s):
    sid, tid, stype, sval, sstat, url, method, headers_json, body = s
    started_at = datetime.utcnow().isoformat()
    start_time = time.time()
    
    status = "failure"
    try:
        headers = json.loads(headers_json)
        req = urllib.request.Request(url, method=method, headers=headers, data=body.encode() if body else None)
        with urllib.request.urlopen(req, timeout=10) as response:
            if response.status < 400:
                status = "success"
    except Exception as e:
        print(f"Request failed: {e}")

    latency = (time.time() - start_time) * 1000
    
    conn = sqlite3.connect('scheduler.db')
    c = conn.cursor()
    c.execute("INSERT INTO runs (schedule_id, status, started_at, latency_ms) VALUES (?, ?, ?, ?)",
              (sid, status, started_at, latency))
    conn.commit()
    conn.close()

# API Handler
class APIHandler(http.server.BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_GET(self):
        self._set_cors()
        path = self.path.split('?')[0]
        if path == '/targets':
            self._send_json(self._get_targets())
        elif path == '/schedules':
            self._send_json(self._get_schedules())
        elif path == '/runs':
            self._send_json(self._get_runs())
        elif path == '/metrics':
            self._send_json(self._get_metrics())
        else:
            self.send_error(404)

    def do_POST(self):
        self._set_cors()
        content_length = int(self.headers.get('Content-Length', 0))
        data = {}
        if content_length > 0:
            data = json.loads(self.rfile.read(content_length))
        
        path = self.path.split('?')[0]

        if path == '/targets':
            tid = self._create_target(data)
            self._send_json({"id": tid}, 201)
        elif path == '/schedules':
            sid = self._create_schedule(data)
            self._send_json({"id": sid}, 201)
        elif path.startswith('/schedules/') and path.endswith('/pause'):
            parts = path.split('/')
            if len(parts) >= 3:
                sid = int(parts[2])
                self._update_schedule_status(sid, 'paused')
                self._send_json({"status": "paused"})
        elif path.startswith('/schedules/') and path.endswith('/resume'):
            parts = path.split('/')
            if len(parts) >= 3:
                sid = int(parts[2])
                self._update_schedule_status(sid, 'active')
                self._send_json({"status": "active"})
        else:
            self.send_error(404)

    def _set_cors(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Content-Type', 'application/json')

    def _send_json(self, data, status=200):
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def _get_targets(self):
        conn = sqlite3.connect('scheduler.db')
        c = conn.cursor()
        c.execute("SELECT id, name, url, method, headers FROM targets")
        ts = [{"id": r[0], "name": r[1], "url": r[2], "method": r[3], "headers": json.loads(r[4]), "created_at": datetime.utcnow().isoformat()} for r in c.fetchall()]
        conn.close()
        return ts

    def _create_target(self, d):
        conn = sqlite3.connect('scheduler.db')
        c = conn.cursor()
        c.execute("INSERT INTO targets (name, url, method, headers, body) VALUES (?, ?, ?, ?, ?)",
                  (d['name'], d['url'], d.get('method', 'GET'), json.dumps(d.get('headers', {})), d.get('body')))
        tid = c.lastrowid
        conn.commit()
        conn.close()
        return tid

    def _get_schedules(self):
        conn = sqlite3.connect('scheduler.db')
        c = conn.cursor()
        # Add basic defaults for missing UI fields
        c.execute("SELECT id, target_id, name, type, value, status FROM schedules")
        ss = [{"id": r[0], "target_id": r[1], "name": r[2], "type": r[3], "value": r[4], "status": r[5], "last_run_at": None, "next_run_at": None, "created_at": datetime.utcnow().isoformat()} for r in c.fetchall()]
        conn.close()
        return ss

    def _create_schedule(self, d):
        conn = sqlite3.connect('scheduler.db')
        c = conn.cursor()
        c.execute("INSERT INTO schedules (target_id, name, type, value, status) VALUES (?, ?, ?, ?, ?)",
                  (d['target_id'], d['name'], d['type'], d['value'], 'active'))
        sid = c.lastrowid
        conn.commit()
        conn.close()
        return sid

    def _update_schedule_status(self, sid, status):
        conn = sqlite3.connect('scheduler.db')
        c = conn.cursor()
        c.execute("UPDATE schedules SET status = ? WHERE id = ?", (status, sid))
        conn.commit()
        conn.close()

    def _get_runs(self):
        conn = sqlite3.connect('scheduler.db')
        c = conn.cursor()
        c.execute("SELECT id, schedule_id, status, started_at, latency_ms FROM runs ORDER BY id DESC LIMIT 50")
        rs = [{"id": r[0], "schedule_id": r[1], "status": r[2], "started_at": r[3], "latency_ms": r[4]} for r in c.fetchall()]
        conn.close()
        return rs

    def _get_metrics(self):
        conn = sqlite3.connect('scheduler.db')
        c = conn.cursor()
        c.execute("SELECT status, latency_ms FROM runs")
        runs = c.fetchall()
        total = len(runs)
        if total == 0: return {"total_runs": 0, "success_rate": 0, "avg_latency_ms": 0}
        successes = sum(1 for r in runs if r[0] == "success")
        avg_lat = sum(r[1] or 0 for r in runs) / total
        conn.close()
        return {"total_runs": total, "success_rate": (successes/total)*100, "avg_latency_ms": avg_lat}

if __name__ == '__main__':
    init_db()
    threading.Thread(target=scheduler_loop, daemon=True).start()
    server = http.server.HTTPServer(('0.0.0.0', 8000), APIHandler)
    print("Lite API Scheduler running on port 8000...")
    server.serve_forever()
