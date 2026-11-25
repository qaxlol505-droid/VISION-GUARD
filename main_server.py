from fastapi import FastAPI, UploadFile, File, Form, BackgroundTasks, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import datetime
import os

# 💡 استدعاء الوحدات المنفصلة
from database import get_db
from models import ThreatLog, FaceLog, SnapshotLog
from telegram_bot import send_telegram_alert

app = FastAPI(title="VisionGuard API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

if not os.path.exists("static/alerts"): os.makedirs("static/alerts")
if not os.path.exists("static/snapshots"): os.makedirs("static/snapshots")
app.mount("/static", StaticFiles(directory="static"), name="static")

# الذاكرة الحية (RAM Cache)
transient_info_logs = []

@app.post("/api/log_threat")
async def log_threat(
    background_tasks: BackgroundTasks, 
    threat_type: str = Form(...), 
    file: UploadFile = File(...),
    db: Session = Depends(get_db)  # 💡 استخدام قاعدة البيانات بأمان
):
    t_type = threat_type.upper()
    now_time = datetime.datetime.now()

    if t_type not in ["PISTOL", "KNIFE", "UNAUTHORIZED"]:
        transient_info_logs.append({
            "threat_type": t_type,
            "timestamp": now_time.strftime("%Y-%m-%d %H:%M:%S"),
            "category": "INFO"
        })
        if len(transient_info_logs) > 30:
            transient_info_logs.pop(0)
        return {"status": "Object sent to UI live feed (Not saved to DB)"}

    file_name = f"{now_time.strftime('%H%M%S')}_{file.filename}"
    file_path = f"static/alerts/{file_name}"
    with open(file_path, "wb") as buffer: 
        buffer.write(await file.read())
    
    if t_type in ["PISTOL", "KNIFE"]:
        db.add(ThreatLog(threat_type=t_type, image_url=f"/static/alerts/{file_name}"))
        background_tasks.add_task(send_telegram_alert, t_type, file_path, now_time.strftime("%Y-%m-%d %H:%M:%S"))
        
    elif t_type == "UNAUTHORIZED":
        db.add(FaceLog(person_name="UNKNOWN", status="UNAUTHORIZED", image_url=f"/static/alerts/{file_name}"))
        background_tasks.add_task(send_telegram_alert, "UNAUTHORIZED", file_path, now_time.strftime("%Y-%m-%d %H:%M:%S"))
    
    db.commit()
    return {"status": "Threat/Unauth Logged securely to DB and Telegram"}

@app.post("/api/log_access")
async def log_access(person_name: str = Form(...), db: Session = Depends(get_db)):
    db.add(FaceLog(person_name=person_name, status="AUTHORIZED", image_url=""))
    db.commit()
    return {"status": "Access Logged successfully", "person": person_name}

@app.post("/api/snapshot")
async def take_snapshot(file: UploadFile = File(...), db: Session = Depends(get_db)):
    file_name = f"SNAP_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
    file_path = f"static/snapshots/{file_name}"
    with open(file_path, "wb") as buffer: 
        buffer.write(await file.read())
    db.add(SnapshotLog(image_url=f"/static/snapshots/{file_name}"))
    db.commit()
    return {"status": "Snapshot saved"}

@app.get("/api/alerts")
def get_alerts(db: Session = Depends(get_db)):
    logs = []
    
    for t in db.query(ThreatLog).order_by(ThreatLog.timestamp.desc()).limit(20).all():
        logs.append({"threat_type": t.threat_type, "timestamp": t.timestamp.strftime("%Y-%m-%d %H:%M:%S"), "category": "THREAT"})
    for f in db.query(FaceLog).order_by(FaceLog.timestamp.desc()).limit(20).all():
        if f.status == "UNAUTHORIZED":
            logs.append({"threat_type": "UNAUTHORIZED", "timestamp": f.timestamp.strftime("%Y-%m-%d %H:%M:%S"), "category": "UNAUTH"})
        else:
            logs.append({"person_name": f.person_name, "timestamp": f.timestamp.strftime("%Y-%m-%d %H:%M:%S"), "category": "VERIFIED"})
    for s in db.query(SnapshotLog).order_by(SnapshotLog.timestamp.desc()).limit(10).all():
        logs.append({"threat_type": "MANUAL SNAPSHOT", "timestamp": s.timestamp.strftime("%Y-%m-%d %H:%M:%S"), "category": "SNAPSHOT"})
    
    logs.extend(transient_info_logs)
    
    return sorted(logs, key=lambda x: x["timestamp"], reverse=True)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)