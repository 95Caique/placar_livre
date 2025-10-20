# live_widget_styled.py
# Requisitos: pip install PyQt6 requests
# Uso: export FOOTBALL_DATA_KEY="sua_chave_aqui" && python live_widget_styled.py

import sys
from datetime import datetime, timezone
import requests
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QListWidget, QListWidgetItem, QPushButton, QFrame, QProgressBar, QGraphicsDropShadowEffect
)
from PyQt6.QtGui import QFont, QPixmap, QImage, QPalette

# ========== CONFIG ==========
from config import API_KEY, API_URL, LOGO_API, POLL_INTERVAL, TIMEOUT


# Cache
_IMG_CACHE = {}
_LOGO_URL = {}

# Demo comentado pois não quero que traga esses dados fixos se não encontrar nenhuma partida, porém
# mantidos para fins de teste caso necessário.
DEMO = [
    # {"id": "1", "home": "Flamengo", "away": "Palmeiras", "home_goals": 2, "away_goals": 1,
    #  "status": "1H", "minute": 38, "home_logo": None, "away_logo": None},
    # {"id": "2", "home": "Corinthians", "away": "São Paulo", "home_goals": 1, "away_goals": 1,
    #  "status": "HT", "minute": 45, "home_logo": None, "away_logo": None},
]


# ========== API ==========
def fetch_matches():
    """Busca partidas ao vivo"""
    if not API_KEY:
        return []
    try:
        r = requests.get(API_URL, headers={"X-Auth-Token": API_KEY}, timeout=10)
        r.raise_for_status()
        matches = []
        for m in r.json().get("matches", []):
            score = m.get("score", {}).get("fullTime", {}) or {}
            matches.append({
                "id": m.get("id"),
                "home": m.get("homeTeam", {}).get("name", "—"),
                "away": m.get("awayTeam", {}).get("name", "—"),
                "home_goals": score.get("home", 0),
                "away_goals": score.get("away", 0),
                "status": m.get("status", ""),
                "minute": m.get("minute"),
                "home_logo": None,
                "away_logo": None,
            })
        return matches
    except:
        return []


def get_logo_url(team):
    """Busca URL do logo no TheSportsDB"""
    if not team or team in _LOGO_URL:
        return _LOGO_URL.get(team)
    try:
        r = requests.get(LOGO_API, params={"t": team}, timeout=TIMEOUT)
        teams = r.json().get("teams", [])
        url = teams[0].get("strTeamBadge") if teams else None
        _LOGO_URL[team] = url
        return url
    except:
        _LOGO_URL[team] = None
        return None


def download_image(url):
    """Baixa e cacheia imagem"""
    if not url or url in _IMG_CACHE:
        return _IMG_CACHE.get(url)
    try:
        r = requests.get(url, timeout=TIMEOUT)
        img = QImage.fromData(r.content)
        _IMG_CACHE[url] = img if not img.isNull() else None
        return _IMG_CACHE[url]
    except:
        _IMG_CACHE[url] = None
        return None


# ========== THREAD ==========
class FetchThread(QThread):
    result = pyqtSignal(object)

    def run(self):
        matches = fetch_matches()
        for m in matches:
            for side in ["home", "away"]:
                url = get_logo_url(m[side])
                m[f"{side}_logo"] = url
                if url and url not in _IMG_CACHE:
                    download_image(url)
        self.result.emit(matches)


# ========== MATCH ITEM ==========
class MatchItem(QWidget):
    def __init__(self, match):
        super().__init__()
        self.m = match
        color = QApplication.palette().color(QPalette.ColorRole.WindowText).name()

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(15)

        # Home
        layout.addLayout(self._team_layout(self.m["home"], self.m["home_logo"], color, False))

        # Score
        score = QLabel(f"{self.m['home_goals']}  —  {self.m['away_goals']}")
        score.setFont(QFont("", 14, QFont.Weight.Bold))
        score.setStyleSheet(f"color: {color};")
        score.setAlignment(Qt.AlignmentFlag.AlignCenter)
        score.setMinimumWidth(70)
        layout.addWidget(score)

        # Away
        layout.addLayout(self._team_layout(self.m["away"], self.m["away_logo"], color, True))

        # Status
        badge = QLabel(f"{self.m['minute']}'" if self.m['minute'] else self.m['status'])
        badge.setFont(QFont("", 8, QFont.Weight.Bold))
        badge.setFixedWidth(55)
        badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        badge.setStyleSheet(self._badge_style())
        layout.addWidget(badge)

    def _team_layout(self, name, logo_url, color, reverse):
        """Layout time (logo + nome)"""
        layout = QHBoxLayout()
        layout.setSpacing(10)

        logo = QLabel()
        logo.setFixedSize(34, 34)
        if logo_url and (img := _IMG_CACHE.get(logo_url)):
            logo.setPixmap(QPixmap.fromImage(img).scaled(34, 34, Qt.AspectRatioMode.KeepAspectRatio))
        else:
            parts = name.split()
            initials = name[:2].upper() if len(parts) == 1 else f"{parts[0][0]}{parts[-1][0]}".upper()
            logo.setText(initials)
            logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
            logo.setStyleSheet(f"color: {color}; font-weight: 700; font-size: 11px; background: transparent;")

        label = QLabel(name)
        label.setFont(QFont("", 10, QFont.Weight.DemiBold))
        label.setStyleSheet(f"color: {color}; background: transparent;")
        label.setMinimumWidth(140)
        if reverse:
            label.setAlignment(Qt.AlignmentFlag.AlignRight)
            layout.addWidget(label, stretch=1)
            layout.addWidget(logo)
        else:
            layout.addWidget(logo)
            layout.addWidget(label, stretch=1)

        return layout

    def _badge_style(self):
        """Estilo do badge de status"""
        s = self.m['status'].upper()
        if s in {"1H", "2H", "LIVE", "HT", "ET"} or self.m['minute']:
            return "background: #ff5b5b; color: white; border-radius: 8px; padding: 6px 4px;"
        elif s in {"FINISHED", "FT", "FT-PEN"}:
            return "background: #e6e8eb; color: #111; border-radius: 8px; padding: 6px 4px;"
        return "background: #eef2f6; color: #223; border-radius: 8px; padding: 6px 4px;"


# ========== MAIN WIDGET ==========
class LiveWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Placar — Série A")
        self.setFixedSize(680, 500)
        self.dark = False
        self.sec = 0

        # UI
        root = QVBoxLayout(self)
        root.setContentsMargins(14, 14, 14, 14)

        self.container = QFrame()
        self.container.setObjectName("container")
        shadow = QGraphicsDropShadowEffect(blurRadius=20, xOffset=0, yOffset=6)
        self.container.setGraphicsEffect(shadow)

        layout = QVBoxLayout(self.container)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(12)

        # Header
        header = QHBoxLayout()
        title = QLabel("Brasileirão — Placar Ao Vivo")
        title.setFont(QFont("", 13, QFont.Weight.Bold))
        header.addWidget(title, stretch=1)

        self.theme_btn = QPushButton("☼")
        self.theme_btn.setFixedSize(34, 34)
        self.theme_btn.clicked.connect(self.toggle_theme)
        header.addWidget(self.theme_btn)

        refresh_btn = QPushButton("⟳")
        refresh_btn.setFixedSize(40, 34)
        refresh_btn.clicked.connect(self.refresh)
        header.addWidget(refresh_btn)
        layout.addLayout(header)

        # List
        self.list = QListWidget()
        self.list.setObjectName("list")
        layout.addWidget(self.list, stretch=1)

        # Footer
        footer = QHBoxLayout()
        self.status = QLabel("Última atualização: —")
        self.status.setFont(QFont("", 9))
        footer.addWidget(self.status)
        footer.addStretch()

        self.progress = QProgressBar()
        self.progress.setMaximum(POLL_INTERVAL)
        self.progress.setValue(POLL_INTERVAL)
        self.progress.setTextVisible(False)
        self.progress.setFixedSize(180, 10)
        footer.addWidget(self.progress)
        layout.addLayout(footer)

        root.addWidget(self.container)

        # Timers
        self.poll_timer = QTimer()
        self.poll_timer.timeout.connect(self.fetch)
        self.poll_timer.start(POLL_INTERVAL * 1000)

        self.tick_timer = QTimer()
        self.tick_timer.timeout.connect(self.tick)
        self.tick_timer.start(1000)

        self.thread = None
        self.apply_theme()
        self.fetch()

    def apply_theme(self):
        """Aqui aplica o tema"""
        if self.dark:
            bg, txt, sub, item, acc = "#0f1720", "#e6eef8", "rgba(230,238,248,0.65)", "rgba(255,255,255,0.04)", "#2aa7ff"
            self.theme_btn.setText("◐")
        else:
            bg, txt, sub, item, acc = "#ffffff", "#0b1220", "rgba(11,18,32,0.55)", "rgba(2,6,23,0.025)", "#2aa7ff"
            self.theme_btn.setText("☼")

        self.container.setStyleSheet(f"QFrame#container {{background: {bg}; border-radius: 16px;}}")
        self.list.setStyleSheet(f"""
            QListWidget#list {{background: transparent; border: none;}}
            QListWidget::item {{background: {item}; margin: 5px 0; padding: 0; border-radius: 12px; color: {txt};}}
            QListWidget::item:hover {{background: rgba(42,167,255,0.08);}}
            QListWidget::item:selected {{background: rgba(42,167,255,0.15);}}
        """)
        self.setStyleSheet(f"""
            QLabel {{color: {txt};}}
            QPushButton {{background: transparent; border: 1px solid rgba(100,100,100,0.15); border-radius: 8px; 
                         padding: 6px; font-size: 16px;}}
            QPushButton:hover {{background: rgba(42,167,255,0.1); border-color: {acc};}}
            QProgressBar {{background: rgba(100,100,100,0.12); border-radius: 5px; border: none;}}
            QProgressBar::chunk {{border-radius: 5px; background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                                 stop:0 {acc}, stop:1 #6ccfff);}}
        """)
        self.status.setStyleSheet(f"color: {sub};")

    def toggle_theme(self):
        self.dark = not self.dark
        self.apply_theme()

    def tick(self):
        self.sec += 1
        self.progress.setValue(max(0, POLL_INTERVAL - self.sec))
        if self.sec >= POLL_INTERVAL:
            self.sec = 0

    def fetch(self):
        if self.thread and self.thread.isRunning():
            return
        self.thread = FetchThread()
        self.thread.result.connect(self.update_list)
        self.thread.start()

    def refresh(self):
        self.sec = 0
        self.progress.setValue(POLL_INTERVAL)
        self.fetch()

    def update_list(self, matches):
        self.list.clear()
        matches_to_show = matches or []  # se matches for None -> []
        if not matches_to_show:
            item = QListWidgetItem("Nenhuma partida ao vivo no momento")
            self.list.addItem(item)
        else:
            for m in matches_to_show:
                item = QListWidgetItem()
                widget = MatchItem(m)
                item.setSizeHint(widget.sizeHint())
                self.list.addItem(item)
                self.list.setItemWidget(item, widget)

        self.status.setText(f"Última atualização: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
        self.sec = 0
        self.progress.setValue(POLL_INTERVAL)


# ========== MAIN ==========
if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = LiveWidget()
    screen = app.primaryScreen().availableGeometry()
    w.move((screen.width() - w.width()) // 2, 60)
    w.show()
    sys.exit(app.exec())