"""
Ana Uygulama — Teknik Servis ve Stok Yönetim Sistemi
Giriş ekranı ve oturum yönetimi
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import bcrypt
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFrame, QFormLayout, QCheckBox, QMessageBox, QWidget
)
from PyQt6.QtCore import Qt
import json
from shared.schema import (
    load_db_config, get_engine, create_all_tables, get_session_factory, migrate_database, CONFIG_PATH, User
)

CRED_PATH = os.path.join(os.path.dirname(CONFIG_PATH), "credentials.json")

def load_credentials():
    if os.path.exists(CRED_PATH):
        try:
            with open(CRED_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            pass
    return {}

def save_credentials(un, pw):
    try:
        with open(CRED_PATH, "w", encoding="utf-8") as f:
            json.dump({"un": un, "pw": pw}, f)
    except:
        pass

def clear_credentials():
    if os.path.exists(CRED_PATH):
        try:
            os.remove(CRED_PATH)
        except:
            pass

STYLE = """
QMainWindow, QDialog, QWidget {
    background-color: #f5f7fa;
    font-family: 'Segoe UI', Arial, sans-serif;
    font-size: 13px;
    color: #2d3748;
}
QPushButton {
    background-color: #3182ce;
    color: white;
    border: none;
    border-radius: 6px;
    padding: 9px 20px;
    font-weight: 600;
    font-size: 13px;
}
QPushButton:hover { background-color: #2b6cb0; }
QPushButton#btnSuccess { background-color: #38a169; color: white; }
QPushButton#btnSuccess:hover { background-color: #2f855a; color: white; }
QPushButton#btnDanger { background-color: #e53e3e; color: white; }
QPushButton#btnDanger:hover { background-color: #c53030; color: white; }
QPushButton#btnSecondary { background-color: #718096; color: white; }
QPushButton#btnSecondary:hover { background-color: #4a5568; color: white; }
QPushButton#btnWarning { background-color: #d69e2e; color: white; }
QPushButton#btnWarning:hover { background-color: #b7791f; color: white; }
QLineEdit, QComboBox, QSpinBox, QTextEdit {
    border: 1.5px solid #cbd5e0;
    border-radius: 6px;
    padding: 7px 10px;
    background: white;
    font-size: 13px;
}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QTextEdit:focus {
    border-color: #3182ce;
}
QTableWidget {
    border: 1px solid #e2e8f0;
    border-radius: 6px;
    gridline-color: #f0f4f8;
    background: white;
    alternate-background-color: #f7fafc;
}
QTableWidget::item:selected {
    background-color: #bee3f8;
    color: #2b6cb0;
}
QHeaderView::section {
    background-color: #edf2f7;
    padding: 8px;
    border: none;
    font-weight: 700;
    color: #4a5568;
}
QTabWidget::pane {
    border: 1px solid #e2e8f0;
    background: white;
}
QTabBar::tab {
    background: #edf2f7;
    color: #4a5568;
    padding: 10px 20px;
    border-radius: 6px 6px 0 0;
    margin-right: 2px;
    font-weight: 500;
}
QTabBar::tab:selected {
    background: white;
    color: #2b6cb0;
    font-weight: 700;
    border-bottom: 3px solid #3182ce;
}
QGroupBox {
    border: 1.5px solid #e2e8f0;
    border-radius: 8px;
    margin-top: 12px;
    padding-top: 12px;
    font-weight: 700;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
    color: #3182ce;
}
QCheckBox::indicator {
    width: 18px; height: 18px;
    border-radius: 4px;
    border: 2px solid #cbd5e0;
}
QCheckBox::indicator:checked {
    background-color: #3182ce;
    border-color: #3182ce;
}
QScrollBar:vertical {
    width: 8px;
    background: #f0f4f8;
}
QScrollBar::handle:vertical {
    background: #cbd5e0;
    border-radius: 4px;
    min-height: 30px;
}
QMessageBox QPushButton {
    background-color: #cbd5e0;
    color: #1a202c;
    border-radius: 4px;
    padding: 6px 14px;
}
QMessageBox QPushButton:hover {
    background-color: #a0aec0;
}
"""


class LoginDialog(QDialog):
    def __init__(self, session, parent=None):
        super().__init__(parent)
        self.session = session
        self.logged_user = None
        self.setWindowTitle("Giriş — Teknik Servis ve Stok Yönetim Sistemi")
        self.setFixedSize(400, 360)
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.WindowCloseButtonHint)
        self._build_ui()
        self._load_creds()

    def _load_creds(self):
        creds = load_credentials()
        if creds.get("un") and creds.get("pw"):
            self.le_user.setText(creds["un"])
            self.le_pass.setText(creds["pw"])
            self.chk_remember.setChecked(True)

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header
        header = QFrame()
        header.setStyleSheet(
            "background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #1a365d,stop:1 #2b6cb0);"
        )
        h_layout = QVBoxLayout(header)
        h_layout.setContentsMargins(25, 22, 25, 22)

        title_lbl = QLabel("🔧 Servis & Stok")
        title_lbl.setStyleSheet("color: white; font-size: 20px; font-weight: bold; background: transparent;")
        sub_lbl = QLabel("Stok & Servis Yönetim Sistemi")
        sub_lbl.setStyleSheet("color: #90cdf4; font-size: 12px; background: transparent;")
        h_layout.addWidget(title_lbl)
        h_layout.addWidget(sub_lbl)
        layout.addWidget(header)

        # Form
        form_w = QWidget()
        form = QFormLayout(form_w)
        form.setContentsMargins(35, 28, 35, 20)
        form.setSpacing(14)

        self.le_user = QLineEdit()
        self.le_user.setPlaceholderText("Kullanıcı adınız")
        self.le_user.setMinimumHeight(38)
        self.le_pass = QLineEdit()
        self.le_pass.setEchoMode(QLineEdit.EchoMode.Password)
        self.le_pass.setPlaceholderText("Şifreniz")
        self.le_pass.setMinimumHeight(38)
        self.le_pass.returnPressed.connect(self._login)

        form.addRow("Kullanıcı Adı:", self.le_user)
        form.addRow("Şifre:", self.le_pass)

        self.chk_remember = QCheckBox("Beni Hatırla")
        form.addRow("", self.chk_remember)

        btn_login = QPushButton("Giriş Yap →")
        btn_login.setMinimumHeight(42)
        btn_login.setObjectName("btnSuccess")
        btn_login.clicked.connect(self._login)
        form.addRow(btn_login)

        self.lbl_error = QLabel("")
        self.lbl_error.setStyleSheet("color: #e53e3e; font-size: 12px;")
        self.lbl_error.setAlignment(Qt.AlignmentFlag.AlignCenter)
        form.addRow(self.lbl_error)

        layout.addWidget(form_w)
        layout.addStretch()

    def _login(self):
        un = self.le_user.text().strip()
        pw = self.le_pass.text()
        if not un or not pw:
            self.lbl_error.setText("Kullanıcı adı ve şifre gerekli.")
            return
        user = self.session.query(User).filter_by(username=un, is_active=True).first()
        if not user:
            self.lbl_error.setText("Kullanıcı bulunamadı veya pasif.")
            return
        if not bcrypt.checkpw(pw.encode(), user.password_hash.encode()):
            self.lbl_error.setText("Şifre hatalı.")
            return
        
        if self.chk_remember.isChecked():
            save_credentials(un, pw)
        else:
            clear_credentials()

        self.logged_user = user
        self.accept()


def get_app_session():
    cfg = load_db_config()
    if not cfg:
        return None, None
    engine = get_engine(cfg)
    create_all_tables(engine)
    migrate_database(engine)
    Session = get_session_factory(engine)
    return engine, Session()


def get_style():
    return STYLE
