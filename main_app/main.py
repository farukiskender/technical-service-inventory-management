"""
Ana Uygulama — Giriş Noktası
"""

import sys
import os
import traceback
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtGui import QFont

def exception_hook(exctype, value, tb):
    error_msg = "".join(traceback.format_exception(exctype, value, tb))
    print("UNCAUGHT EXCEPTION:\n", error_msg, file=sys.stderr)
    try:
        log_path = os.path.join(os.path.dirname(__file__), "..", "app_crash.log")
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"\n--- {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ---\n{error_msg}\n")
    except Exception:
        pass
    if QApplication.instance():
        QMessageBox.critical(None, "Uygulama Hatası", f"Bir hata oluştu:\n{value}\n\nDetaylar app_crash.log dosyasına kaydedildi.")
    else:
        sys.__excepthook__(exctype, value, tb)

sys.excepthook = exception_hook

from main_app.login import LoginDialog, get_app_session, get_style
from main_app.main_window import MainWindow
from shared.schema import CONFIG_PATH


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Teknik Servis ve Stok Yonetim Sistemi")
    app.setFont(QFont("Segoe UI", 12))
    app.setStyle("Fusion")          # Sistem temasını devre dışı bırak
    app.setStyleSheet(get_style())

    # Check DB config
    if not os.path.exists(CONFIG_PATH):
        QMessageBox.warning(
            None, "Yapılandırma Eksik",
            "Veritabanı yapılandırması bulunamadı.\n"
            "Lütfen önce Admin Panelini çalıştırıp kurulumu tamamlayın."
        )
        sys.exit(1)

    engine, session = get_app_session()
    if not session:
        QMessageBox.critical(None, "Hata", "Veritabanına bağlanılamadı.")
        sys.exit(1)

    while True:
        login = LoginDialog(session)
        if login.exec() == 0:
            break

        window = MainWindow(session, login.logged_user)
        window.showMaximized()
        app.exec()
        
        if getattr(window, "logout_requested", False):
            window.deleteLater()
            continue
        else:
            break
            
    sys.exit(0)


if __name__ == "__main__":
    main()
