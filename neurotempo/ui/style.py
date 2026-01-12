APP_QSS = """
/* ---- Base ---- */
QMainWindow, QWidget {
    background: #0b0f14;
    color: #e7eef7;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Inter, Arial;
    font-size: 14px;
}

QLabel {
    color: #e7eef7;
}

QPushButton {
    background: #1f2937;
    border: 1px solid rgba(255,255,255,0.10);
    padding: 10px 14px;
    border-radius: 12px;
    font-weight: 600;
}
QPushButton:hover { background: #263244; }
QPushButton:pressed { background: #1b2431; }
QPushButton:disabled {
    color: rgba(231,238,247,0.35);
    background: rgba(31,41,55,0.35);
    border: 1px solid rgba(255,255,255,0.06);
}

QProgressBar {
    border: 1px solid rgba(255,255,255,0.10);
    border-radius: 10px;
    background: rgba(255,255,255,0.06);
    text-align: center;
    height: 20px;
}
QProgressBar::chunk {
    border-radius: 10px;
}

/* Make plot widgets blend in */
PlotWidget {
    background: transparent;
}

/* Small muted text helper */
QLabel#muted {
    color: rgba(231,238,247,0.70);
}
"""