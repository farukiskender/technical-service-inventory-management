"""
Ana Uygulama — Main Window
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QStackedWidget, QSizePolicy, QSpacerItem,
    QMessageBox, QApplication, QScrollArea, QTableWidget, QTableWidgetItem,
    QHeaderView, QGroupBox
)
from PyQt6.QtCore import Qt, QSize, QEvent, QPoint, pyqtSignal, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QFont, QColor, QIcon, QCursor, QMouseEvent

from main_app.ui.products_page import ProductsPage
from main_app.ui.stock_page import StockPage, btn, get_stock_level
from main_app.ui.service_page import ServicePage, STATUS_COLOR_MAP, ServiceDetailDialog, ServiceFormDialog
from main_app.ui.persons_page import PersonsPage

NAV_ITEMS = [
    ("🏠", "Ana Sayfa", "home"),
    ("📦", "Ürünler", "products"),
    ("📊", "Stok", "stock"),
    ("🔧", "Teknik Servis", "service"),
    ("👥", "Müşteriler", "persons"),
]

class NavButton(QPushButton):
    def __init__(self, icon, label, key, parent=None):
        super().__init__(parent)
        self.key = key
        self._icon_text = icon
        self._label_text = label
        self.setCheckable(True)
        self.setText(f" {icon}  {label} ")
        self.setFont(QFont("Segoe UI", 10))
        self.setFixedHeight(36)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._update_style(False)

    def _update_style(self, active):
        if active:
            self.setStyleSheet("""
                QPushButton {
                    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #1e40af,stop:1 #2563eb);
                    color: white;
                    border: none;
                    border-radius: 6px;
                    padding: 0 12px;
                    font-weight: bold;
                    margin: 0 2px;
                }
            """)
        else:
            self.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    color: #94a3b8;
                    border: none;
                    border-radius: 6px;
                    padding: 0 12px;
                    font-weight: 500;
                    margin: 0 2px;
                }
                QPushButton:hover {
                    background-color: #1e293b;
                    color: white;
                }
            """)

    def setActive(self, active):
        self._update_style(active)


class DashboardPage(QWidget):
    def __init__(self, session, user, on_navigate=None):
        super().__init__()
        self.session = session
        self.user = user
        self.on_navigate = on_navigate
        self._val_labels = {}
        self._status_labels = {}
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        container = QWidget()
        container.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(22, 16, 22, 16)
        layout.setSpacing(14)

        # ── 1. Hoş geldiniz banner
        welcome_frame = QFrame()
        welcome_frame.setObjectName("welcomeFrame")
        welcome_frame.setStyleSheet("""
            #welcomeFrame {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #0f172a,stop:0.5 #1e3a5f,stop:1 #1e40af);
                border-radius: 10px;
            }
        """)
        welcome_frame.setFixedHeight(72)
        wl = QHBoxLayout(welcome_frame)
        wl.setContentsMargins(20, 10, 20, 10)

        text_col = QVBoxLayout()
        text_col.setSpacing(2)
        title = QLabel(f"Hoş Geldiniz, {self.user.full_name}! 👋")
        title.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        title.setStyleSheet("color: white; background: transparent;")

        user_title = getattr(self.user, 'title', None) or ''
        sub = QLabel(user_title if user_title else self.user.role.name)
        sub.setStyleSheet("color: #93c5fd; font-size: 11px; background: transparent;")

        text_col.addWidget(title)
        text_col.addWidget(sub)
        wl.addLayout(text_col)
        wl.addStretch()
        layout.addWidget(welcome_frame)

        # ── 2. İstatistik Sayaç Kartları
        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(10)

        cards = [
            ("products", "Aktif Ürün", "#10b981", "#ecfdf5"),
            ("wh", "Depo", "#f59e0b", "#fffbeb"),
            ("services", "Açık Servis", "#3b82f6", "#eff6ff"),
            ("persons", "Müşteri / Kişi", "#8b5cf6", "#f5f3ff"),
        ]

        for key, label, color, bg in cards:
            card = QFrame()
            card.setStyleSheet(f"""
                QFrame {{
                    background: {bg};
                    border: 1.5px solid {color}30;
                    border-radius: 8px;
                }}
            """)
            cl = QVBoxLayout(card)
            cl.setContentsMargins(14, 10, 14, 10)
            cl.setSpacing(2)
            val_lbl = QLabel("0")
            val_lbl.setFont(QFont("Segoe UI", 22, QFont.Weight.Bold))
            val_lbl.setStyleSheet(f"color: {color}; background: transparent;")
            val_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            name_lbl = QLabel(label)
            name_lbl.setStyleSheet("color: #64748b; font-size: 11px; font-weight: 600; background: transparent;")
            name_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            cl.addWidget(val_lbl)
            cl.addWidget(name_lbl)
            stats_layout.addWidget(card)
            self._val_labels[key] = val_lbl

        layout.addLayout(stats_layout)

        # ── 3. Hızlı İşlemler Çubuğu
        action_bar = QFrame()
        action_bar.setStyleSheet("background: white; border: 1px solid #e2e8f0; border-radius: 8px; padding: 6px;")
        abl = QHBoxLayout(action_bar)
        abl.setContentsMargins(12, 6, 12, 6)
        abl.setSpacing(10)

        act_title = QLabel("⚡ Hızlı İşlemler:")
        act_title.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        act_title.setStyleSheet("color: #334155;")
        abl.addWidget(act_title)

        if getattr(self.user.role, 'can_create', True):
            btn_new_srv = btn("➕ Yeni Servis Kaydı", "primary", height=30)
            btn_new_srv.clicked.connect(self._quick_new_service)
            abl.addWidget(btn_new_srv)

        btn_go_stock = btn("📦 Stok İşlemleri", "secondary", height=30)
        btn_go_stock.clicked.connect(lambda: self.on_navigate("stock") if self.on_navigate else None)
        abl.addWidget(btn_go_stock)

        if getattr(self.user.role, 'can_create', True):
            btn_go_prod = btn("🏷️ Ürünler", "secondary", height=30)
            btn_go_prod.clicked.connect(lambda: self.on_navigate("products") if self.on_navigate else None)
            abl.addWidget(btn_go_prod)

            btn_go_cust = btn("👥 Müşteri Ekle", "secondary", height=30)
            btn_go_cust.clicked.connect(lambda: self.on_navigate("persons") if self.on_navigate else None)
            abl.addWidget(btn_go_cust)

        abl.addStretch()
        layout.addWidget(action_bar)

        # ── 4. İki Sütunlu Alt Gövde (Son Servisler + Durum/Kritik Stok)
        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(14)

        # Sol Kolon: Son Servis Kayıtları
        left_box = QGroupBox("🔧 Son Servis Talepleri (Son 8 Kayıt)")
        left_box.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        lbl_layout = QVBoxLayout(left_box)
        lbl_layout.setContentsMargins(10, 10, 10, 10)
        lbl_layout.setSpacing(8)

        self.table_recent = QTableWidget()
        self.table_recent.setColumnCount(5)
        self.table_recent.setHorizontalHeaderLabels(["Servis No", "Cihaz / Model", "Müşteri", "Durum", "Tarih"])
        hh = self.table_recent.horizontalHeader()
        hh.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        hh.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        hh.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.table_recent.verticalHeader().setVisible(False)
        self.table_recent.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table_recent.setAlternatingRowColors(True)
        self.table_recent.itemDoubleClicked.connect(self._open_service_detail)
        self.table_recent.setMinimumHeight(240)
        lbl_layout.addWidget(self.table_recent)

        tip_lbl = QLabel("💡 Bir servis kaydına çift tıklayarak detay ve parça yönetimini açabilirsiniz.")
        tip_lbl.setStyleSheet("color: #94a3b8; font-size: 11px;")
        lbl_layout.addWidget(tip_lbl)
        bottom_row.addWidget(left_box, 3)

        # Sağ Kolon: Durum Dağılımı ve Kritik Stok
        right_panel = QVBoxLayout()
        right_panel.setSpacing(12)

        # A) Durum Dağılımı
        box_dist = QGroupBox("📊 Servis Durum Dağılımı")
        box_dist.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        bd_layout = QVBoxLayout(box_dist)
        bd_layout.setSpacing(6)
        bd_layout.setContentsMargins(10, 8, 10, 8)

        self._status_labels = {}
        status_items = [
            ("received", "Kayıt / İncelemede", "#f59e0b", "#fffbeb"),
            ("waiting", "Onay Bekliyor", "#6366f1", "#eef2ff"),
            ("repaired", "Onarıldı (Hazır)", "#10b981", "#ecfdf5"),
            ("delivered", "Teslim Edildi", "#06b6d4", "#ecfeff"),
        ]
        for key, s_title, col, sbg in status_items:
            s_row = QFrame()
            s_row.setStyleSheet(f"background: {sbg}; border-radius: 6px; padding: 4px;")
            srl = QHBoxLayout(s_row)
            srl.setContentsMargins(8, 4, 8, 4)
            st_lbl = QLabel(s_title)
            st_lbl.setStyleSheet(f"color: #1e293b; font-size: 11px; font-weight: 600; background: transparent;")
            val = QLabel("0")
            val.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
            val.setStyleSheet(f"color: {col}; background: transparent;")
            srl.addWidget(st_lbl)
            srl.addStretch()
            srl.addWidget(val)
            bd_layout.addWidget(s_row)
            self._status_labels[key] = val

        right_panel.addWidget(box_dist)

        # B) Kritik / Azalan Stok Paneli
        box_low = QGroupBox("⚠️ Kritik / Azalan Stok")
        box_low.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        bl_layout = QVBoxLayout(box_low)
        bl_layout.setContentsMargins(8, 8, 8, 8)
        bl_layout.setSpacing(6)

        self.table_low_stock = QTableWidget()
        self.table_low_stock.setColumnCount(2)
        self.table_low_stock.setHorizontalHeaderLabels(["Ürün", "Kalan Stok"])
        self.table_low_stock.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table_low_stock.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table_low_stock.verticalHeader().setVisible(False)
        self.table_low_stock.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table_low_stock.setMaximumHeight(150)
        bl_layout.addWidget(self.table_low_stock)

        right_panel.addWidget(box_low)
        bottom_row.addLayout(right_panel, 2)

        layout.addLayout(bottom_row)

        scroll.setWidget(container)
        root.addWidget(scroll)
        self.refresh()

    def _quick_new_service(self):
        dlg = ServiceFormDialog(self.session, self.user, parent=self)
        if dlg.exec() == ServiceFormDialog.DialogCode.Accepted:
            self.refresh()
            if self.on_navigate:
                self.on_navigate("service")

    def _open_service_detail(self, item):
        row = item.row()
        srv_item = self.table_recent.item(row, 0)
        if not srv_item:
            return
        srv_id = srv_item.data(Qt.ItemDataRole.UserRole)
        if srv_id:
            dlg = ServiceDetailDialog(self.session, self.user, srv_id, parent=self)
            dlg.exec()
            self.refresh()

    def refresh(self):
        from shared.schema import Product, Warehouse, ServiceRecord, Person
        try:
            total_products = self.session.query(Product).filter_by(is_active=True).count()
            total_wh = self.session.query(Warehouse).filter_by(is_active=True).count()
            open_services = self.session.query(ServiceRecord).filter(~ServiceRecord.status.in_(["Teslim Edildi", "İptal Edildi"])).count()
            total_persons = self.session.query(Person).filter_by(is_active=True).count()

            self._val_labels["products"].setText(str(total_products))
            self._val_labels["wh"].setText(str(total_wh))
            self._val_labels["services"].setText(str(open_services))
            self._val_labels["persons"].setText(str(total_persons))

            # Durum Dağılımı
            c_recv = self.session.query(ServiceRecord).filter(ServiceRecord.status.in_(["Kayıt Alındı", "İncelemede"])).count()
            c_wait = self.session.query(ServiceRecord).filter(ServiceRecord.status == "Onay Bekliyor").count()
            c_rep = self.session.query(ServiceRecord).filter(ServiceRecord.status == "Onarıldı").count()
            c_del = self.session.query(ServiceRecord).filter(ServiceRecord.status == "Teslim Edildi").count()

            if "received" in self._status_labels:
                self._status_labels["received"].setText(str(c_recv))
            if "waiting" in self._status_labels:
                self._status_labels["waiting"].setText(str(c_wait))
            if "repaired" in self._status_labels:
                self._status_labels["repaired"].setText(str(c_rep))
            if "delivered" in self._status_labels:
                self._status_labels["delivered"].setText(str(c_del))

            # Son 8 Servis Kaydı
            recent_services = self.session.query(ServiceRecord).order_by(ServiceRecord.created_at.desc()).limit(8).all()
            self.table_recent.setRowCount(len(recent_services))
            for r_idx, s in enumerate(recent_services):
                self.table_recent.setRowHeight(r_idx, 32)

                item_no = QTableWidgetItem(s.service_no)
                item_no.setData(Qt.ItemDataRole.UserRole, s.id)
                item_no.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table_recent.setItem(r_idx, 0, item_no)

                self.table_recent.setItem(r_idx, 1, QTableWidgetItem(s.device_info or "—"))
                self.table_recent.setItem(r_idx, 2, QTableWidgetItem(s.customer_name or "—"))

                # Durum rozet hücresi
                status_color, status_bg = STATUS_COLOR_MAP.get(s.status, ("#64748b", "#f1f5f9"))
                item_st = QTableWidgetItem(f" {s.status} ")
                item_st.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                item_st.setForeground(QColor(status_color))
                item_st.setBackground(QColor(status_bg))
                item_st.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
                self.table_recent.setItem(r_idx, 3, item_st)

                dt_str = s.created_at.strftime("%d.%m.%Y") if s.created_at else "—"
                item_dt = QTableWidgetItem(dt_str)
                item_dt.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table_recent.setItem(r_idx, 4, item_dt)

            # Kritik Stok Kontrolü (Stoğu <= 15 olan veya en az stoğu kalan ilk 5 ürün)
            all_prods = self.session.query(Product).filter_by(is_active=True).all()
            all_whs = self.session.query(Warehouse).filter_by(is_active=True).all()
            prod_stocks = []
            for p in all_prods:
                tot = sum(get_stock_level(self.session, p.id, w.id) for w in all_whs)
                prod_stocks.append((p.name, tot, p.unit))

            prod_stocks.sort(key=lambda x: x[1])
            critical_stocks = [x for x in prod_stocks if x[1] <= 15][:5]
            if not critical_stocks and prod_stocks:
                # Eğer 15 altı yoksa en düşük 3 ürünü bilgi amaçlı göster
                critical_stocks = prod_stocks[:3]

            self.table_low_stock.setRowCount(len(critical_stocks))
            for l_idx, (p_name, lvl, unit) in enumerate(critical_stocks):
                self.table_low_stock.setRowHeight(l_idx, 28)
                self.table_low_stock.setItem(l_idx, 0, QTableWidgetItem(p_name))
                lvl_str = f"{lvl:.1f}".rstrip("0").rstrip(".") + f" {unit}"
                item_lvl = QTableWidgetItem(lvl_str)
                item_lvl.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                if lvl <= 5:
                    item_lvl.setForeground(QColor("#e53e3e"))
                    item_lvl.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
                else:
                    item_lvl.setForeground(QColor("#d69e2e"))
                self.table_low_stock.setItem(l_idx, 1, item_lvl)

        except Exception as e:
            pass


class MainWindow(QMainWindow):
    def __init__(self, session, user):
        super().__init__()
        self.session = session
        self.user = user
        self.logout_requested = False

        self.setWindowTitle("Teknik Servis ve Stok Yönetim Sistemi")
        self.setMinimumSize(960, 600)
        self._pages = {}
        self._nav_btns = {}
        self._build_ui()
        self._switch_page("home")

    def _build_ui(self):
        central = QWidget()
        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # ─── Top Navbar ─────────────────────────────────────────────
        top_navbar = QFrame()
        top_navbar.setFixedHeight(54)
        top_navbar.setObjectName("topNavbar")
        top_navbar.setStyleSheet("""
            #topNavbar {
                background: qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 #0f172a,stop:1 #1e293b);
                border-bottom: 2px solid #1e40af;
            }
        """)
        nav_layout = QHBoxLayout(top_navbar)
        nav_layout.setContentsMargins(12, 0, 12, 0)
        nav_layout.setSpacing(4)
        
        # Logo
        logo_widget = QWidget()
        logo_widget.setStyleSheet("background: transparent;")
        logo_l = QHBoxLayout(logo_widget)
        logo_l.setContentsMargins(0, 0, 0, 0)
        logo_l.setSpacing(8)

        self._logo_icon = QLabel("⚡")
        self._logo_icon.setStyleSheet("color: #38bdf8; font-size: 20px; background: transparent;")
        
        logo_text_col = QVBoxLayout()
        logo_text_col.setContentsMargins(0, 0, 0, 0)
        logo_text_col.setSpacing(0)
        self._logo_title = QLabel("SERVİS & STOK")
        self._logo_title.setStyleSheet("color: white; font-size: 13px; font-weight: bold; background: transparent;")
        self._logo_sub = QLabel("Otomasyon & Servis")
        self._logo_sub.setStyleSheet("color: #60a5fa; font-size: 9px; font-weight: 600; background: transparent;")
        logo_text_col.addWidget(self._logo_title)
        logo_text_col.addWidget(self._logo_sub)

        logo_l.addWidget(self._logo_icon)
        logo_l.addLayout(logo_text_col)
        nav_layout.addWidget(logo_widget)
        nav_layout.addSpacing(16)
        
        # Nav items
        for icon, label, key in NAV_ITEMS:
            btn = NavButton(icon, label, key)
            btn.clicked.connect(lambda _, k=key: self._switch_page(k))
            nav_layout.addWidget(btn)
            self._nav_btns[key] = btn
            
        nav_layout.addStretch()
        
        # User details & Logout
        self._user_avatar = QLabel("👤")
        self._user_avatar.setStyleSheet("color: #60a5fa; font-size: 20px; background: transparent;")
        
        self._u_col_widget = QWidget()
        self._u_col_widget.setStyleSheet("background: transparent;")
        u_col = QVBoxLayout(self._u_col_widget)
        u_col.setSpacing(1)
        u_col.setContentsMargins(4, 8, 8, 8)
        self._u_name_lbl = QLabel(self.user.full_name)
        self._u_name_lbl.setStyleSheet("color: white; font-size: 12px; font-weight: bold; background: transparent;")
        self._u_role_lbl = QLabel(self.user.role.name)
        self._u_role_lbl.setStyleSheet("color: #60a5fa; font-size: 11px; background: transparent;")
        u_col.addWidget(self._u_name_lbl)
        u_col.addWidget(self._u_role_lbl)
        
        from main_app.ui.stock_page import btn
        self._btn_logout = btn("Çıkış", "danger", height=28)
        self._btn_logout.clicked.connect(self._logout)
        
        nav_layout.addWidget(self._user_avatar)
        nav_layout.addWidget(self._u_col_widget)
        nav_layout.addWidget(self._btn_logout)
        
        root_layout.addWidget(top_navbar)
        
        # ─── Main content area ────────────────────────────────────
        content_area = QFrame()
        content_area.setStyleSheet("background: #f8fafc;")
        ca_layout = QVBoxLayout(content_area)
        ca_layout.setContentsMargins(0, 0, 0, 0)
        ca_layout.setSpacing(0)
        
        # Page Title Bar
        title_bar = QFrame()
        title_bar.setFixedHeight(50)
        title_bar.setStyleSheet("background: white; border-bottom: 1px solid #e2e8f0;")
        tb_layout = QHBoxLayout(title_bar)
        tb_layout.setContentsMargins(20, 0, 20, 0)
        self.page_title_lbl = QLabel("Ana Sayfa")
        self.page_title_lbl.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        self.page_title_lbl.setStyleSheet("color: #1e293b;")
        tb_layout.addWidget(self.page_title_lbl)
        tb_layout.addStretch()
        ca_layout.addWidget(title_bar)
        
        # Pages
        self.stack = QStackedWidget()
        ca_layout.addWidget(self.stack)
        
        root_layout.addWidget(content_area)
        self.setCentralWidget(central)
        
        # Initialize pages
        self._pages["home"] = DashboardPage(self.session, self.user, on_navigate=self._switch_page)
        self._pages["products"] = ProductsPage(self.session, self.user)
        self._pages["stock"] = StockPage(self.session, self.user)
        self._pages["service"] = ServicePage(self.session, self.user)
        self._pages["persons"] = PersonsPage(self.session, self.user)
        
        for page in self._pages.values():
            self.stack.addWidget(page)

    def _switch_page(self, key):
        page_titles = {
            "home": "Ana Sayfa",
            "products": "Ürün Tanımları",
            "stock": "Stok Yönetimi",
            "service": "Teknik Servis Yönetimi",
            "persons": "Müşteriler ve Kişiler",
        }
        # Update nav buttons
        for k, btn in self._nav_btns.items():
            btn.setActive(k == key)

        # Refresh page if it exists
        page = self._pages.get(key)
        if page:
            self.stack.setCurrentWidget(page)
            if hasattr(page, 'refresh'):
                page.refresh()

        self.page_title_lbl.setText(page_titles.get(key, key))

    def _logout(self):
        reply = QMessageBox.question(self, 'Çıkış', 'Çıkış yapmak istediğinize emin misiniz?',
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.logout_requested = True
            self.close()
