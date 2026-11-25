import datetime
from PyQt6.QtGui import QTextDocument, QPdfWriter

def generate_pdf_report(cached_logs, filename_prefix="VisionGuard_Structured_Report"):
    if not cached_logs: return False
    
    try:
        filename = f"{filename_prefix}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        writer = QPdfWriter(filename)
        
        threats = [log for log in cached_logs if log[1] == "THREAT"]
        faces = [log for log in cached_logs if log[1] in ["VERIFIED", "UNAUTH"]]
        
        html = f"""
        <h1 style='color: #2c3e50; font-family: sans-serif; text-align: center;'>VisionGuard AI Security Report</h1>
        <p style='font-family: sans-serif; color: #555; text-align: center;'><b>Generated on:</b> {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        <hr>
        """
        
        html += "<h2 style='color: #2980b9; font-family: sans-serif;'>1. Personnel & Access Log (Faces)</h2>"
        html += "<table border='1' width='100%' cellspacing='0' cellpadding='8' style='border-collapse: collapse; font-family: sans-serif; text-align: left;'>"
        html += "<tr style='background-color: #ebf5fc;'><th>Timestamp</th><th>Event Details</th><th>Status</th></tr>"
        for event, status, ts in faces: 
            c = "green" if status=="VERIFIED" else "orange"
            html += f"<tr><td>{ts}</td><td>{event}</td><td style='color:{c};'><b>{status}</b></td></tr>"
        html += "</table><br>"
        
        html += "<h2 style='color: #e74c3c; font-family: sans-serif;'>2. Critical Threats (Weapons)</h2>"
        html += "<table border='1' width='100%' cellspacing='0' cellpadding='8' style='border-collapse: collapse; font-family: sans-serif; text-align: left;'>"
        html += "<tr style='background-color: #fceceb;'><th>Timestamp</th><th>Event Details</th></tr>"
        for event, status, ts in threats: html += f"<tr><td>{ts}</td><td>{event}</td></tr>"
        html += "</table><br>"
        
        doc = QTextDocument()
        doc.setHtml(html)
        doc.print(writer)
        return True
    except Exception as e:
        print(f"PDF Export Error: {e}")
        return False