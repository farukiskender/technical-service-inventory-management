"""
Admin Uygulaması — Ana Pencere ve Kurulum Sihirbazı
Teknik Servis ve Stok Yönetim Sistemi
"""

import sys
import os
import json

# shared modülünü bul
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import bcrypt
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QLineEdit, QComboBox, QFormLayout,
    QMessageBox, QTabWidget, QTableWidget, QTableWidgetItem,
    QDialog, QDialogButtonBox, QCheckBox, QHeaderView, QFrame,
    QSpacerItem, QSizePolicy, QGroupBox, QSpinBox, QStackedWidget,
    QFileDialog
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont, QColor, QPalette, QIcon, QPixmap

from shared.schema import (
    Role, User, Warehouse, load_db_config, save_db_config,
    get_engine, create_all_tables, get_session_factory, CONFIG_PATH
)
from main_app.ui.stock_page import btn
from main_app.login import load_credentials, save_credentials, clear_credentials


# ─── Stil Sabitler ────────────────────────────────────────────────────────────

STYLE = """
QMainWindow, QDialog, QWidget {
    background-color: #f5f7fa;
    font-family: 'Segoe UI', Arial, sans-serif;
    font-size: 13px;
    color: #2d3748;
}
QTabWidget::pane {
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    background: white;
}
QTabBar::tab {
    background: #edf2f7;
    color: #4a5568;
    padding: 10px 22px;
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
QPushButton {
    background-color: #3182ce;
    color: white;
    border: none;
    border-radius: 6px;
    padding: 8px 18px;
    font-weight: 600;
    font-size: 13px;
}
QPushButton:hover {
    background-color: #2b6cb0;
}
QPushButton:pressed {
    background-color: #2c5282;
}
QPushButton#btnDanger {
    background-color: #e53e3e;
    color: white;
}
QPushButton#btnDanger:hover {
    background-color: #c53030;
    color: white;
}
QPushButton#btnSecondary {
    background-color: #718096;
    color: white;
}
QPushButton#btnSecondary:hover {
    background-color: #4a5568;
    color: white;
}
QPushButton#btnSuccess {
    background-color: #38a169;
    color: white;
}
QPushButton#btnSuccess:hover {
    background-color: #2f855a;
    color: white;
}
QLineEdit, QComboBox, QSpinBox {
    border: 1.5px solid #cbd5e0;
    border-radius: 6px;
    padding: 7px 10px;
    background: white;
    font-size: 13px;
}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus {
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
QGroupBox {
    border: 1.5px solid #e2e8f0;
    border-radius: 8px;
    margin-top: 12px;
    padding-top: 12px;
    font-weight: 700;
    color: #2d3748;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
    color: #3182ce;
}
QCheckBox {
    spacing: 8px;
}
QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border-radius: 4px;
    border: 2px solid #cbd5e0;
}
QCheckBox::indicator:checked {
    background-color: #3182ce;
    border-color: #3182ce;
}
"""

HEADER_STYLE = """
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #2b6cb0, stop:1 #3182ce);
    border-radius: 0px;
    padding: 0px;
"""


# ─── DB Bağlantı Testi Thread ─────────────────────────────────────────────────

class TestConnectionThread(QThread):
    result = pyqtSignal(bool, str)

    def __init__(self, config):
        super().__init__()
        self.config = config

    def run(self):
        try:
            engine = get_engine(self.config)
            with engine.connect() as conn:
                pass
            self.result.emit(True, "Bağlantı başarılı!")
        except Exception as e:
            self.result.emit(False, str(e))


# ─── DB Kurulum Sayfası ───────────────────────────────────────────────────────

class DatabaseSetupPage(QWidget):
    setup_complete = pyqtSignal()

    def __init__(self):
        super().__init__()
        self._build_ui()
        self._load_existing()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 20, 30, 20)
        layout.setSpacing(15)

        title = QLabel("Veritabanı Motoru ve Bağlantısı")
        title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        title.setStyleSheet("color: #2b6cb0;")
        layout.addWidget(title)

        # DB Type Selector
        type_row = QHBoxLayout()
        type_row.addWidget(QLabel("Veritabanı Türü:"))
        self.cb_db_type = QComboBox()
        self.cb_db_type.addItems(["SQLite", "PostgreSQL", "MSSQL (SQL Server)"])
        self.cb_db_type.currentIndexChanged.connect(self._on_type_changed)
        type_row.addWidget(self.cb_db_type)
        type_row.addStretch()
        layout.addLayout(type_row)

        # Stacked Widget for settings
        self.settings_stack = QStackedWidget()

        # Page 0: SQLite
        sqlite_w = QWidget()
        sl = QVBoxLayout(sqlite_w)
        sl.setContentsMargins(0, 0, 0, 0)
        self.sqlite_group = QGroupBox("SQLite Dosya Konumu")
        sg_layout = QHBoxLayout(self.sqlite_group)
        self.sqlite_path = QLineEdit("teknik_servis.db")
        self.sqlite_path.setPlaceholderText("Dosya adı veya tam yol")
        btn_browse = QPushButton("Gözat")
        btn_browse.setObjectName("btnSecondary")
        btn_browse.setFixedWidth(80)
        btn_browse.clicked.connect(self._browse_sqlite)
        sg_layout.addWidget(self.sqlite_path)
        sg_layout.addWidget(btn_browse)
        sl.addWidget(self.sqlite_group)
        self.settings_stack.addWidget(sqlite_w)

        # Page 1: PostgreSQL
        pg_w = QWidget()
        pg_l = QVBoxLayout(pg_w)
        pg_l.setContentsMargins(0, 0, 0, 0)
        pg_grp = QGroupBox("PostgreSQL Sunucu Bilgileri")
        pg_form = QFormLayout(pg_grp)
        pg_form.setSpacing(10)
        self.pg_host = QLineEdit("localhost")
        self.pg_port = QSpinBox()
        self.pg_port.setRange(1, 65535)
        self.pg_port.setValue(5432)
        self.pg_db = QLineEdit("teknik_servis")
        self.pg_user = QLineEdit("postgres")
        self.pg_pass = QLineEdit()
        self.pg_pass.setEchoMode(QLineEdit.EchoMode.Password)
        pg_form.addRow("Sunucu (Host):", self.pg_host)
        pg_form.addRow("Port:", self.pg_port)
        pg_form.addRow("Veritabanı Adı:", self.pg_db)
        pg_form.addRow("Kullanıcı:", self.pg_user)
        pg_form.addRow("Şifre:", self.pg_pass)
        pg_l.addWidget(pg_grp)
        self.settings_stack.addWidget(pg_w)

        # Page 2: MSSQL
        ms_w = QWidget()
        ms_l = QVBoxLayout(ms_w)
        ms_l.setContentsMargins(0, 0, 0, 0)
        ms_grp = QGroupBox("MSSQL (SQL Server) Sunucu Bilgileri")
        ms_form = QFormLayout(ms_grp)
        ms_form.setSpacing(10)
        self.ms_host = QLineEdit("localhost")
        self.ms_port = QSpinBox()
        self.ms_port.setRange(1, 65535)
        self.ms_port.setValue(1433)
        self.ms_db = QLineEdit("teknik_servis")
        self.ms_user = QLineEdit("sa")
        self.ms_pass = QLineEdit()
        self.ms_pass.setEchoMode(QLineEdit.EchoMode.Password)
        self.ms_driver = QLineEdit("ODBC Driver 17 for SQL Server")
        ms_form.addRow("Sunucu (Host):", self.ms_host)
        ms_form.addRow("Port:", self.ms_port)
        ms_form.addRow("Veritabanı Adı:", self.ms_db)
        ms_form.addRow("Kullanıcı:", self.ms_user)
        ms_form.addRow("Şifre:", self.ms_pass)
        ms_form.addRow("ODBC Driver:", self.ms_driver)
        ms_l.addWidget(ms_grp)
        self.settings_stack.addWidget(ms_w)

        layout.addWidget(self.settings_stack)

        # Butonlar
        btn_layout = QHBoxLayout()
        self.btn_test = QPushButton("Bağlantıyı Test Et")
        self.btn_test.setObjectName("btnSecondary")
        self.btn_setup = QPushButton("Veritabanını Kur ve Kaydet")
        self.btn_setup.setObjectName("btnSuccess")
        self.test_result_label = QLabel("")
        btn_layout.addWidget(self.btn_test)
        btn_layout.addWidget(self.btn_setup)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        layout.addWidget(self.test_result_label)
        layout.addStretch()

        self.btn_test.clicked.connect(self._test_connection)
        self.btn_setup.clicked.connect(self._setup_db)

    def _on_type_changed(self, idx):
        self.settings_stack.setCurrentIndex(idx)

    def _browse_sqlite(self):
        path, _ = QFileDialog.getSaveFileName(self, "SQLite Dosyası", "", "SQLite (*.db *.sqlite)")
        if path:
            self.sqlite_path.setText(path)

    def _build_config(self):
        idx = self.cb_db_type.currentIndex()
        if idx == 0:
            return {"type": "sqlite", "path": self.sqlite_path.text().strip()}
        elif idx == 1:
            return {
                "type": "postgresql",
                "host": self.pg_host.text().strip(),
                "port": self.pg_port.value(),
                "database": self.pg_db.text().strip(),
                "user": self.pg_user.text().strip(),
                "password": self.pg_pass.text()
            }
        else:
            return {
                "type": "mssql",
                "host": self.ms_host.text().strip(),
                "port": self.ms_port.value(),
                "database": self.ms_db.text().strip(),
                "user": self.ms_user.text().strip(),
                "password": self.ms_pass.text(),
                "driver": self.ms_driver.text().strip()
            }

    def _test_connection(self):
        self.test_result_label.setText("Test ediliyor...")
        self.test_result_label.setStyleSheet("color: #718096;")
        config = self._build_config()
        self._thread = TestConnectionThread(config)
        self._thread.result.connect(self._on_test_result)
        self._thread.start()

    def _on_test_result(self, ok, msg):
        if ok:
            self.test_result_label.setText(f"✓ {msg}")
            self.test_result_label.setStyleSheet("color: #38a169; font-weight: bold;")
        else:
            self.test_result_label.setText(f"✗ {msg}")
            self.test_result_label.setStyleSheet("color: #e53e3e; font-weight: bold;")

    def _setup_db(self):
        config = self._build_config()
        try:
            engine = get_engine(config)
            create_all_tables(engine)
            save_db_config(config)
            self.test_result_label.setText("✓ Veritabanı kuruldu ve ayarlar kaydedildi.")
            self.test_result_label.setStyleSheet("color: #38a169; font-weight: bold;")
            self.setup_complete.emit()
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Veritabanı kurulumu başarısız:\n{e}")

    def _load_existing(self):
        cfg = load_db_config()
        if not cfg:
            return
        t = cfg.get("type", "sqlite").lower()
        if t == "sqlite":
            self.cb_db_type.setCurrentIndex(0)
            self.sqlite_path.setText(cfg.get("path", "teknik_servis.db"))
        elif t in ("postgresql", "postgres"):
            self.cb_db_type.setCurrentIndex(1)
            self.pg_host.setText(cfg.get("host", "localhost"))
            self.pg_port.setValue(cfg.get("port", 5432))
            self.pg_db.setText(cfg.get("database", "teknik_servis"))
            self.pg_user.setText(cfg.get("user", "postgres"))
            self.pg_pass.setText(cfg.get("password", ""))
        elif t in ("mssql", "sqlserver"):
            self.cb_db_type.setCurrentIndex(2)
            self.ms_host.setText(cfg.get("host", "localhost"))
            self.ms_port.setValue(cfg.get("port", 1433))
            self.ms_db.setText(cfg.get("database", "teknik_servis"))
            self.ms_user.setText(cfg.get("user", "sa"))
            self.ms_pass.setText(cfg.get("password", ""))
            self.ms_driver.setText(cfg.get("driver", "ODBC Driver 17 for SQL Server"))


# ─── Kullanıcı Yönetimi ───────────────────────────────────────────────────────

class UserDialog(QDialog):
    def __init__(self, session, user=None, parent=None):
        super().__init__(parent)
        self.session = session
        self.user = user
        self.setWindowTitle("Kullanıcı" if not user else "Kullanıcı Düzenle")
        self.setMinimumWidth(400)
        self._build_ui()
        if user:
            self._load_user()

    def _build_ui(self):
        layout = QFormLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)

        self.le_fullname = QLineEdit()
        self.le_username = QLineEdit()
        self.le_password = QLineEdit()
        self.le_password.setEchoMode(QLineEdit.EchoMode.Password)
        self.le_password.setPlaceholderText("Boş bırakılırsa değişmez" if self.user else "Şifre")
        self.le_title = QLineEdit()
        self.le_title.setPlaceholderText("Ünvan (örn: Teknik Servis Müdürü)")
        self.cb_role = QComboBox()
        self.roles = self.session.query(Role).all()
        for r in self.roles:
            self.cb_role.addItem(r.name, r.id)
        self.chk_active = QCheckBox("Aktif")
        self.chk_active.setChecked(True)

        layout.addRow("Ad Soyad:", self.le_fullname)
        layout.addRow("Kullanıcı Adı:", self.le_username)
        layout.addRow("Şifre:", self.le_password)
        layout.addRow("Ünvan:", self.le_title)
        layout.addRow("Rol:", self.cb_role)
        layout.addRow("", self.chk_active)

        btns_layout = QHBoxLayout()
        btns_layout.addStretch()
        btn_cancel = btn("İptal", "danger")
        btn_cancel.clicked.connect(self.reject)
        btn_save = btn("Kaydet", "success")
        btn_save.clicked.connect(self._save)
        btns_layout.addWidget(btn_cancel)
        btns_layout.addWidget(btn_save)
        layout.addRow(btns_layout)

    def _load_user(self):
        self.le_fullname.setText(self.user.full_name)
        self.le_username.setText(self.user.username)
        self.le_title.setText(self.user.title or "")
        self.chk_active.setChecked(self.user.is_active)
        idx = self.cb_role.findData(self.user.role_id)
        if idx >= 0:
            self.cb_role.setCurrentIndex(idx)

    def _save(self):
        fn = self.le_fullname.text().strip()
        un = self.le_username.text().strip()
        pw = self.le_password.text()
        if not fn or not un:
            QMessageBox.warning(self, "Uyarı", "Ad soyad ve kullanıcı adı zorunludur.")
            return
        if not self.user and not pw:
            QMessageBox.warning(self, "Uyarı", "Yeni kullanıcı için şifre zorunludur.")
            return

        role_id = self.cb_role.currentData()
        user_title = self.le_title.text().strip() or None
        try:
            if self.user:
                self.user.full_name = fn
                self.user.username = un
                self.user.title = user_title
                self.user.role_id = role_id
                self.user.is_active = self.chk_active.isChecked()
                if pw:
                    self.user.password_hash = bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()
            else:
                pw_hash = bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()
                u = User(full_name=fn, username=un, password_hash=pw_hash,
                         title=user_title,
                         role_id=role_id, is_active=self.chk_active.isChecked())
                self.session.add(u)
            self.session.commit()
            self.accept()
        except Exception as e:
            self.session.rollback()
            QMessageBox.critical(self, "Hata", str(e))


class UsersPage(QWidget):
    def __init__(self, session):
        super().__init__()
        self.session = session
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 15, 20, 15)
        layout.setSpacing(12)

        title = QLabel("Kullanıcı Yönetimi")
        title.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        title.setStyleSheet("color: #2b6cb0;")

        btn_add = QPushButton("+ Yeni Kullanıcı")
        btn_add.setObjectName("btnSuccess")
        btn_add.setFixedWidth(150)
        btn_add.clicked.connect(self._add_user)

        top = QHBoxLayout()
        top.addWidget(title)
        top.addStretch()
        top.addWidget(btn_add)
        layout.addLayout(top)

        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["ID", "Ad Soyad", "Kullanıcı Adı", "Rol", "Durum", "İşlem"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.table)

    def refresh(self):
        users = self.session.query(User).join(Role).all()
        self.table.setRowCount(len(users))
        for i, u in enumerate(users):
            self.table.setItem(i, 0, QTableWidgetItem(str(u.id)))
            self.table.setItem(i, 1, QTableWidgetItem(u.full_name))
            self.table.setItem(i, 2, QTableWidgetItem(u.username))
            self.table.setItem(i, 3, QTableWidgetItem(u.role.name))
            status_item = QTableWidgetItem("Aktif" if u.is_active else "Pasif")
            status_item.setForeground(QColor("#38a169") if u.is_active else QColor("#e53e3e"))
            self.table.setItem(i, 4, status_item)

            btn_edit = QPushButton("Düzenle")
            btn_edit.setFixedHeight(28)
            btn_edit.clicked.connect(lambda _, uid=u.id: self._edit_user(uid))
            self.table.setCellWidget(i, 5, btn_edit)

    def _add_user(self):
        dlg = UserDialog(self.session, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.refresh()

    def _edit_user(self, uid):
        u = self.session.query(User).get(uid)
        dlg = UserDialog(self.session, user=u, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.refresh()


# ─── Rol Yönetimi ─────────────────────────────────────────────────────────────

class RoleDialog(QDialog):
    def __init__(self, session, role=None, parent=None):
        super().__init__(parent)
        self.session = session
        self.role = role
        self.setWindowTitle("Rol Tanımla")
        self.setMinimumWidth(350)
        self._build_ui()
        if role:
            self._load()

    def _build_ui(self):
        layout = QFormLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)
        self.le_name = QLineEdit()
        self.chk_view = QCheckBox("Görüntüleme")
        self.chk_view.setChecked(True)
        self.chk_create = QCheckBox("Oluşturma")
        self.chk_edit = QCheckBox("Düzenleme")
        self.chk_delete = QCheckBox("Silme/Pasifleştirme")
        self.chk_manage = QCheckBox("Yönetim")

        layout.addRow("Rol Adı:", self.le_name)
        for chk in [self.chk_view, self.chk_create, self.chk_edit, self.chk_delete, self.chk_manage]:
            layout.addRow("", chk)

        btns_layout = QHBoxLayout()
        btns_layout.addStretch()
        btn_cancel = btn("İptal", "danger")
        btn_cancel.clicked.connect(self.reject)
        btn_save = btn("Kaydet", "success")
        btn_save.clicked.connect(self._save)
        btns_layout.addWidget(btn_cancel)
        btns_layout.addWidget(btn_save)
        layout.addRow(btns_layout)

    def _load(self):
        self.le_name.setText(self.role.name)
        self.chk_view.setChecked(self.role.can_view)
        self.chk_create.setChecked(self.role.can_create)
        self.chk_edit.setChecked(self.role.can_edit)
        self.chk_delete.setChecked(self.role.can_delete)
        self.chk_manage.setChecked(self.role.can_manage)

    def _save(self):
        name = self.le_name.text().strip()
        if not name:
            QMessageBox.warning(self, "Uyarı", "Rol adı boş olamaz.")
            return
        try:
            if self.role:
                r = self.role
            else:
                r = Role()
                self.session.add(r)
            r.name = name
            r.can_view = self.chk_view.isChecked()
            r.can_create = self.chk_create.isChecked()
            r.can_edit = self.chk_edit.isChecked()
            r.can_delete = self.chk_delete.isChecked()
            r.can_manage = self.chk_manage.isChecked()
            self.session.commit()
            self.accept()
        except Exception as e:
            self.session.rollback()
            QMessageBox.critical(self, "Hata", str(e))


class RolesPage(QWidget):
    def __init__(self, session):
        super().__init__()
        self.session = session
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 15, 20, 15)
        layout.setSpacing(12)

        title = QLabel("Rol Yönetimi")
        title.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        title.setStyleSheet("color: #2b6cb0;")

        btn_add = QPushButton("+ Yeni Rol")
        btn_add.setObjectName("btnSuccess")
        btn_add.setFixedWidth(130)
        btn_add.clicked.connect(self._add_role)

        top = QHBoxLayout()
        top.addWidget(title)
        top.addStretch()
        top.addWidget(btn_add)
        layout.addLayout(top)

        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels(["Rol Adı", "Görüntüleme", "Oluşturma", "Düzenleme", "Silme", "Yönetim", "İşlem"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.table)

    def refresh(self):
        roles = self.session.query(Role).all()
        self.table.setRowCount(len(roles))
        for i, r in enumerate(roles):
            self.table.setItem(i, 0, QTableWidgetItem(r.name))
            for j, val in enumerate([r.can_view, r.can_create, r.can_edit, r.can_delete, r.can_manage]):
                item = QTableWidgetItem("✓" if val else "—")
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                item.setForeground(QColor("#38a169") if val else QColor("#a0aec0"))
                self.table.setItem(i, j + 1, item)
            btn_edit = QPushButton("Düzenle")
            btn_edit.setFixedHeight(28)
            btn_edit.clicked.connect(lambda _, rid=r.id: self._edit_role(rid))
            self.table.setCellWidget(i, 6, btn_edit)

    def _add_role(self):
        dlg = RoleDialog(self.session, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.refresh()

    def _edit_role(self, rid):
        r = self.session.query(Role).get(rid)
        dlg = RoleDialog(self.session, role=r, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.refresh()


# ─── Depo Yönetimi ────────────────────────────────────────────────────────────

class WarehouseDialog(QDialog):
    def __init__(self, session, warehouse=None, parent=None):
        super().__init__(parent)
        self.session = session
        self.warehouse = warehouse
        self.setWindowTitle("Depo Tanımla")
        self.setMinimumWidth(380)
        self._build_ui()
        if warehouse:
            self._load()

    def _build_ui(self):
        layout = QFormLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)
        self.le_name = QLineEdit()
        self.le_location = QLineEdit()
        self.le_desc = QLineEdit()
        self.chk_active = QCheckBox("Aktif")
        self.chk_active.setChecked(True)
        layout.addRow("Depo Adı *:", self.le_name)
        layout.addRow("Konum:", self.le_location)
        layout.addRow("Açıklama:", self.le_desc)
        layout.addRow("", self.chk_active)
        btns_layout = QHBoxLayout()
        btns_layout.addStretch()
        btn_cancel = btn("İptal", "danger")
        btn_cancel.clicked.connect(self.reject)
        btn_save = btn("Kaydet", "success")
        btn_save.clicked.connect(self._save)
        btns_layout.addWidget(btn_cancel)
        btns_layout.addWidget(btn_save)
        layout.addRow(btns_layout)

    def _load(self):
        self.le_name.setText(self.warehouse.name)
        self.le_location.setText(self.warehouse.location or "")
        self.le_desc.setText(self.warehouse.description or "")
        self.chk_active.setChecked(self.warehouse.is_active)

    def _save(self):
        name = self.le_name.text().strip()
        if not name:
            QMessageBox.warning(self, "Uyarı", "Depo adı zorunludur.")
            return
        try:
            if self.warehouse:
                w = self.warehouse
            else:
                w = Warehouse()
                self.session.add(w)
            w.name = name
            w.location = self.le_location.text().strip()
            w.description = self.le_desc.text().strip()
            w.is_active = self.chk_active.isChecked()
            self.session.commit()
            self.accept()
        except Exception as e:
            self.session.rollback()
            QMessageBox.critical(self, "Hata", str(e))


class WarehousesPage(QWidget):
    def __init__(self, session):
        super().__init__()
        self.session = session
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 15, 20, 15)
        layout.setSpacing(12)

        title = QLabel("Depo Yönetimi")
        title.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        title.setStyleSheet("color: #2b6cb0;")

        btn_add = QPushButton("+ Yeni Depo")
        btn_add.setObjectName("btnSuccess")
        btn_add.setFixedWidth(130)
        btn_add.clicked.connect(self._add)

        top = QHBoxLayout()
        top.addWidget(title)
        top.addStretch()
        top.addWidget(btn_add)
        layout.addLayout(top)

        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Depo Adı", "Konum", "Açıklama", "Durum", "İşlem"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.table)

    def refresh(self):
        rows = self.session.query(Warehouse).all()
        self.table.setRowCount(len(rows))
        for i, w in enumerate(rows):
            self.table.setItem(i, 0, QTableWidgetItem(w.name))
            self.table.setItem(i, 1, QTableWidgetItem(w.location or ""))
            self.table.setItem(i, 2, QTableWidgetItem(w.description or ""))
            s = QTableWidgetItem("Aktif" if w.is_active else "Pasif")
            s.setForeground(QColor("#38a169") if w.is_active else QColor("#e53e3e"))
            self.table.setItem(i, 3, s)
            btn_edit = QPushButton("Düzenle")
            btn_edit.setFixedHeight(28)
            btn_edit.clicked.connect(lambda _, wid=w.id: self._edit(wid))
            self.table.setCellWidget(i, 4, btn_edit)

    def _add(self):
        dlg = WarehouseDialog(self.session, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.refresh()

    def _edit(self, wid):
        w = self.session.query(Warehouse).get(wid)
        dlg = WarehouseDialog(self.session, warehouse=w, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.refresh()


# ─── İlk Kurulum Sihirbazı ───────────────────────────────────────────────────

class SetupWizard(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("İlk Kurulum Sihirbazı")
        self.setMinimumSize(600, 400)
        self.session = None
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        # Header
        header = QFrame()
        header.setStyleSheet("background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #2b6cb0,stop:1 #3182ce); border-radius:0;")
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(20, 15, 20, 15)
        logo = QLabel("🔧 Servis & Stok Yönetimi")
        logo.setStyleSheet("color: white; font-size: 20px; font-weight: bold; background: transparent;")
        subtitle = QLabel("İlk Kurulum")
        subtitle.setStyleSheet("color: #bee3f8; font-size: 13px; background: transparent;")
        h_layout.addWidget(logo)
        h_layout.addStretch()
        h_layout.addWidget(subtitle)
        layout.addWidget(header)

        # Stacked
        self.stack = QStackedWidget()

        # Sayfa 1: DB Kurulum
        self.db_page = DatabaseSetupPage()
        self.db_page.setup_complete.connect(self._on_db_ready)
        self.stack.addWidget(self.db_page)

        # Sayfa 2: Admin kullanıcı oluştur
        admin_widget = QWidget()
        af_layout = QFormLayout(admin_widget)
        af_layout.setContentsMargins(40, 30, 40, 30)
        af_layout.setSpacing(14)

        title2 = QLabel("Admin Hesabı Oluştur")
        title2.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        title2.setStyleSheet("color: #2b6cb0;")
        af_layout.addRow(title2)

        self.admin_fullname = QLineEdit()
        self.admin_fullname.setText("Sistem Yöneticisi")
        self.admin_username = QLineEdit()
        self.admin_username.setText("admin")
        self.admin_password = QLineEdit()
        self.admin_password.setEchoMode(QLineEdit.EchoMode.Password)
        self.admin_password2 = QLineEdit()
        self.admin_password2.setEchoMode(QLineEdit.EchoMode.Password)

        af_layout.addRow("Ad Soyad:", self.admin_fullname)
        af_layout.addRow("Kullanıcı Adı:", self.admin_username)
        af_layout.addRow("Şifre:", self.admin_password)
        af_layout.addRow("Şifre (tekrar):", self.admin_password2)

        btn_create_admin = QPushButton("Admin Hesabı Oluştur ve Bitir")
        btn_create_admin.setObjectName("btnSuccess")
        btn_create_admin.clicked.connect(self._create_admin)
        af_layout.addRow(btn_create_admin)
        self.stack.addWidget(admin_widget)

        layout.addWidget(self.stack)

    def _on_db_ready(self):
        cfg = load_db_config()
        engine = get_engine(cfg)
        Session = get_session_factory(engine)
        self.session = Session()
        self.stack.setCurrentIndex(1)

    def _create_admin(self):
        fn = self.admin_fullname.text().strip()
        un = self.admin_username.text().strip()
        pw = self.admin_password.text()
        pw2 = self.admin_password2.text()

        if not fn or not un or not pw:
            QMessageBox.warning(self, "Uyarı", "Tüm alanlar zorunludur.")
            return
        if pw != pw2:
            QMessageBox.warning(self, "Uyarı", "Şifreler eşleşmiyor.")
            return

        try:
            # Admin rolü oluştur
            admin_role = Role(
                name="Yönetici",
                can_view=True, can_create=True,
                can_edit=True, can_delete=True, can_manage=True
            )
            viewer_role = Role(
                name="Görüntüleyici",
                can_view=True, can_create=False,
                can_edit=False, can_delete=False, can_manage=False
            )
            operator_role = Role(
                name="Operatör",
                can_view=True, can_create=True,
                can_edit=True, can_delete=False, can_manage=False
            )
            self.session.add_all([admin_role, viewer_role, operator_role])
            self.session.flush()

            pw_hash = bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()
            admin_user = User(
                full_name=fn, username=un,
                password_hash=pw_hash, role_id=admin_role.id, is_active=True
            )
            self.session.add(admin_user)
            self.session.commit()
            QMessageBox.information(self, "Başarılı", "Kurulum tamamlandı! Admin paneline yönlendiriliyorsunuz.")
            self.accept()
        except Exception as e:
            self.session.rollback()
            QMessageBox.critical(self, "Hata", str(e))


# ─── Admin Giriş Ekranı ───────────────────────────────────────────────────────

class AdminLoginDialog(QDialog):
    def __init__(self, session, parent=None):
        super().__init__(parent)
        self.session = session
        self.logged_user = None
        self.setWindowTitle("Admin Girişi")
        self.setFixedSize(380, 340)
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

        header = QFrame()
        header.setStyleSheet("background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #2b6cb0,stop:1 #3182ce);")
        h_layout = QVBoxLayout(header)
        h_layout.setContentsMargins(20, 20, 20, 20)
        lbl = QLabel("🔧 Admin Paneli")
        lbl.setStyleSheet("color: white; font-size: 18px; font-weight: bold; background: transparent;")
        sub = QLabel("Teknik Servis ve Stok Yönetim Sistemi")
        sub.setStyleSheet("color: #bee3f8; font-size: 11px; background: transparent;")
        h_layout.addWidget(lbl)
        h_layout.addWidget(sub)
        layout.addWidget(header)

        form_widget = QWidget()
        form = QFormLayout(form_widget)
        form.setContentsMargins(30, 25, 30, 20)
        form.setSpacing(12)

        self.le_user = QLineEdit()
        self.le_user.setPlaceholderText("Kullanıcı adı")
        self.le_pass = QLineEdit()
        self.le_pass.setEchoMode(QLineEdit.EchoMode.Password)
        self.le_pass.setPlaceholderText("Şifre")
        self.le_pass.returnPressed.connect(self._login)

        form.addRow("Kullanıcı:", self.le_user)
        form.addRow("Şifre:", self.le_pass)

        self.chk_remember = QCheckBox("Beni Hatırla")
        form.addRow("", self.chk_remember)

        btn_login = QPushButton("Giriş Yap")
        btn_login.setObjectName("btnSuccess")
        btn_login.clicked.connect(self._login)
        form.addRow(btn_login)

        self.lbl_error = QLabel("")
        self.lbl_error.setStyleSheet("color: #e53e3e;")
        form.addRow(self.lbl_error)
        layout.addWidget(form_widget)

    def _login(self):
        un = self.le_user.text().strip()
        pw = self.le_pass.text()
        user = self.session.query(User).filter_by(username=un, is_active=True).first()
        if not user:
            self.lbl_error.setText("Kullanıcı bulunamadı.")
            return
        if not bcrypt.checkpw(pw.encode(), user.password_hash.encode()):
            self.lbl_error.setText("Şifre hatalı.")
            return
        if not user.role.can_manage:
            self.lbl_error.setText("Admin yetkisi yok.")
            return

        if self.chk_remember.isChecked():
            save_credentials(un, pw)
        else:
            clear_credentials()

        self.logged_user = user
        self.accept()


# ─── Ana Admin Pencere ────────────────────────────────────────────────────────

class AdminMainWindow(QMainWindow):
    def __init__(self, session, user):
        super().__init__()
        self.session = session
        self.user = user
        self.setWindowTitle("Admin Paneli — Teknik Servis ve Stok Yönetim Sistemi")
        self.setMinimumSize(900, 650)
        self._build_ui()

    def _build_ui(self):
        central = QWidget()
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Header
        header = QFrame()
        header.setStyleSheet(HEADER_STYLE)
        header.setFixedHeight(60)
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(20, 0, 20, 0)

        logo = QLabel("🔧 Admin Paneli")
        logo.setStyleSheet("color: white; font-size: 18px; font-weight: bold; background: transparent;")
        user_lbl = QLabel(f"Hoş geldiniz, {self.user.full_name}")
        user_lbl.setStyleSheet("color: #bee3f8; background: transparent;")
        h_layout.addWidget(logo)
        h_layout.addStretch()
        h_layout.addWidget(user_lbl)
        main_layout.addWidget(header)

        # Tabs
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)

        self.db_tab = DatabaseSetupPage()
        self.users_tab = UsersPage(session=self.session)
        self.roles_tab = RolesPage(session=self.session)
        self.wh_tab = WarehousesPage(session=self.session)

        self.tabs.addTab(self.db_tab, "💾 Veritabanı")
        self.tabs.addTab(self.users_tab, "👥 Kullanıcılar")
        self.tabs.addTab(self.roles_tab, "🔐 Roller")
        self.tabs.addTab(self.wh_tab, "🏭 Depolar")

        main_layout.addWidget(self.tabs)
        self.setCentralWidget(central)


# ─── Uygulama Giriş Noktası ───────────────────────────────────────────────────

def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Servis Stok Admin")
    app.setStyle("Fusion")          # Sistem temasını devre dışı bırak
    app.setStyleSheet(STYLE)

    cfg = load_db_config()

    # İlk kurulum
    if not cfg:
        wizard = SetupWizard()
        if wizard.exec() != QDialog.DialogCode.Accepted:
            sys.exit(0)
        cfg = load_db_config()

    # DB bağlantısı
    try:
        engine = get_engine(cfg)
        create_all_tables(engine)
        Session = get_session_factory(engine)
        session = Session()
    except Exception as e:
        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.critical(None, "Veritabanı Hatası",
                             f"Veritabanına bağlanılamadı:\n{e}\n\nAdmin panelini yeniden başlatın.")
        # Kurulumu sıfırla
        if os.path.exists(CONFIG_PATH):
            os.remove(CONFIG_PATH)
        sys.exit(1)

    # Giriş
    login = AdminLoginDialog(session)
    if login.exec() != QDialog.DialogCode.Accepted:
        sys.exit(0)

    window = AdminMainWindow(session, login.logged_user)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
