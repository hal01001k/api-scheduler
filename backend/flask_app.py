from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
import requests
import time
import json

app = Flask(__name__)
CORS(app)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///scheduler.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Models
class Target(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    url = db.Column(db.String(500), nullable=False)
    method = db.Column(db.String(10), default="GET")
    headers = db.Column(db.Text, default="{}")
    body = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Schedule(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    target_id = db.Column(db.Integer, db.ForeignKey('target.id'))
    name = db.Column(db.String(100), nullable=False)
    type = db.Column(db.String(20)) # interval, cron
    value = db.Column(db.String(100))
    status = db.Column(db.String(20), default="active")
    last_run_at = db.Column(db.DateTime)

class Run(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    schedule_id = db.Column(db.Integer, db.ForeignKey('schedule.id'))
    status = db.Column(db.String(20))
    started_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime)
    latency_ms = db.Column(db.Float)

# Scheduler
scheduler = BackgroundScheduler()

def execute_request(schedule_id):
    with app.app_context():
        schedule = Schedule.query.get(schedule_id)
        if not schedule or schedule.status != "active":
            return

        target = Target.query.get(schedule.target_id)
        if not target:
            return

        run = Run(schedule_id=schedule_id, status="running", started_at=datetime.utcnow())
        db.session.add(run)
        db.session.commit()

        start_time = time.time()
        status_code = None
        error_msg = None

        try:
            headers = json.loads(target.headers)
            resp = requests.request(
                method=target.method,
                url=target.url,
                headers=headers,
                data=target.body,
                timeout=30
            )
            status_code = resp.status_code
        except Exception as e:
            error_msg = str(e)

        end_time = time.time()
        latency = (end_time - start_time) * 1000

        run.status = "success" if status_code and status_code < 400 else "failure"
        run.completed_at = datetime.utcnow()
        run.latency_ms = latency
        schedule.last_run_at = run.started_at
        db.session.commit()

# Routes
@app.route('/targets', methods=['GET', 'POST'])
def handle_targets():
    if request.method == 'POST':
        data = request.json
        target = Target(
            name=data['name'],
            url=data['url'],
            method=data.get('method', 'GET'),
            headers=json.dumps(data.get('headers', {})),
            body=data.get('body')
        )
        db.session.add(target)
        db.session.commit()
        return jsonify({"id": target.id, "name": target.name}), 201
    
    targets = Target.query.all()
    return jsonify([{
        "id": t.id, "name": t.name, "url": t.url, "method": t.method, 
        "headers": json.loads(t.headers), "created_at": t.created_at.isoformat()
    } for t in targets])

@app.route('/schedules', methods=['GET', 'POST'])
def handle_schedules():
    if request.method == 'POST':
        data = request.json
        sched = Schedule(
            name=data['name'],
            target_id=data['target_id'],
            type=data['type'],
            value=data['value'],
            status="active"
        )
        db.session.add(sched)
        db.session.commit()
        
        # Add to APScheduler
        if sched.type == "interval":
            scheduler.add_job(execute_request, 'interval', seconds=int(sched.value), id=str(sched.id), args=[sched.id])
        
        return jsonify({"id": sched.id}), 201

    schedules = Schedule.query.all()
    return jsonify([{
        "id": s.id, "name": s.name, "target_id": s.target_id, "type": s.type, 
        "value": s.value, "status": s.status, "last_run_at": s.last_run_at.isoformat() if s.last_run_at else None
    } for s in schedules])

@app.route('/schedules/<int:id>/<action>', methods=['POST'])
def handle_schedule_action(id, action):
    sched = Schedule.query.get_or_404(id)
    if action == 'pause':
        sched.status = "paused"
        scheduler.pause_job(str(id))
    elif action == 'resume':
        sched.status = "active"
        scheduler.resume_job(str(id))
    db.session.commit()
    return jsonify({"status": sched.status})

@app.route('/runs', methods=['GET'])
def get_runs():
    runs = Run.query.order_by(Run.started_at.desc()).limit(50).all()
    return jsonify([{
        "id": r.id, "schedule_id": r.schedule_id, "status": r.status,
        "started_at": r.started_at.isoformat(), "latency_ms": r.latency_ms
    } for r in runs])

@app.route('/metrics', methods=['GET'])
def get_metrics():
    runs = Run.query.all()
    total = len(runs)
    if total == 0:
        return jsonify({"total_runs": 0, "success_rate": 0, "avg_latency_ms": 0})
    successes = sum(1 for r in runs if r.status == "success")
    avg_lat = sum(r.latency_ms or 0 for r in runs) / total
    return jsonify({
        "total_runs": total,
        "success_rate": (successes / total) * 100,
        "avg_latency_ms": avg_lat
    })

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        # Resume active schedules
        active = Schedule.query.filter_by(status="active").all()
        for s in active:
            if s.type == "interval":
                scheduler.add_job(execute_request, 'interval', seconds=int(s.value), id=str(s.id), args=[s.id])
    scheduler.start()
    app.run(host='0.0.0.0', port=8000, debug=False)
