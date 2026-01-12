import sys

if sys.platform == "darwin":
    FONT_STACK = 'Helvetica Neue","Arial'
elif sys.platform.startswith("win"):
    FONT_STACK = 'Segoe UI","Arial'
else:
    FONT_STACK = 'DejaVu Sans","Arial'

APP_QSS = f"""
QMainWindow, QWidget {{
    background: #0b0f14;
    color: #e7eef7;
    font-family: "{FONT_STACK}";
    font-size: 14px;
}}

QLabel {{
    color: #e7eef7;
}}

QLabel#muted {{
    color: rgba(231,238,247,0.70);
}}

QPushButton {{
    background: #1f2937;
    border: 1px solid rgba(255,255,255,0.10);
    padding: 10px 14px;
    border-radius: 12px;
    font-weight: 600;
}}
QPushButton:hover {{ background: #263244; }}
QPushButton:pressed {{ background: #1b2431; }}

QProgressBar {{
    border: 1px solid rgba(255,255,255,0.10);
    border-radius: 10px;
    background: rgba(255,255,255,0.06);
    text-align: center;
    height: 20px;
}}
QProgressBar::chunk {{
    border-radius: 10px;
}}
"""