"""
Teknik Servis Modülü — Servis kaydı, durum takibi, yedek parça kullanımı ve teslim yönetimi
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from datetime import datetime
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QDialog, QFormLayout,
    QLineEdit, QComboBox, QTextEdit, QHeaderView, QMessageBox,
    QDoubleSpinBox, QFrame, QScrollArea, QGroupBox, QSizePolicy
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QColor

from shared.schema import (
    ServiceRecord, ServiceItem, ServiceHistory,
    Person, Product, Warehouse, StockMovement, SerialNumber, User
)
from shared.utils import tr_contains
from main_app.ui.stock_page import (
    btn, maximize_dialog, SearchableSelector,
    get_stock_level, get_available_serials, SerialSelectDialog
)


# ─── Servis Durumları ve Renkleri ─────────────────────────────────────────────

SERVICE_STATUSES = [
    ("Kayıt Alındı", "#f59e0b", "#fffbeb"),     # Amber
    ("İncelemede", "#0ea5e9", "#f0f9ff"),      # Mavi
    ("Onay Bekliyor", "#6366f1", "#eef2ff"),   # İndigo
    ("Onarıldı", "#10b981", "#ecfdf5"),        # Yeşil
    ("Teslim Edildi", "#06b6d4", "#ecfeff"),   # Camgöbeği
    ("İptal Edildi", "#ef4444", "#fef2f2"),    # Kırmızı
]
STATUS_COLOR_MAP = {s[0]: (s[1], s[2]) for s in SERVICE_STATUSES}


def generate_service_no(session):
    """Benzersiz ve sıralı SRV-00001 formatında servis numarası üretir."""
    last = session.query(ServiceRecord).order_by(ServiceRecord.id.desc()).first()
    next_id = (last.id + 1) if last else 1
    return f"SRV-{next_id:05d}"


# ─── Servis Kayıt / Düzenleme Formu ──────────────────────────────────────────

class ServiceFormDialog(QDialog):
    """Yeni servis kaydı veya düzenleme — ürün ekleme bölümü detay ekranında yapılır."""

    def __init__(self, session, user, record=None, parent=None):
        super().__init__(parent)
        self.session = session
        self.user = user
        self.record = record
        self.setWindowTitle("Yeni Servis Kaydı" if not record else f"Servis Düzenle — {record.service_no}")
        self.setMinimumSize(600, 480)
        maximize_dialog(self)
        self._build_ui()
        if record:
            self._load()

    def _build_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(18, 16, 18, 16)
        root_layout.setSpacing(12)

        # Başlık Banner
        header = QFrame()
        header.setStyleSheet("""
            background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #1a365d,stop:1 #2b6cb0);
            border-radius: 8px;
        """)
        hl = QHBoxLayout(header)
        hl.setContentsMargins(16, 10, 16, 10)
        header_title = QLabel("🔧 Servis Kaydı Formu" if not self.record else f"🔧 Servis Kaydı: {self.record.service_no}")
        header_title.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        header_title.setStyleSheet("color: white; background: transparent;")
        hl.addWidget(header_title)
        root_layout.addWidget(header)

        # Scroll Alanı
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        container = QWidget()
        container.setStyleSheet("background: transparent;")
        form_layout = QVBoxLayout(container)
        form_layout.setSpacing(14)
        form_layout.setContentsMargins(4, 4, 4, 4)

        # ── Grup 1: Servis & Müşteri Bilgileri
        grp_cust = QGroupBox("Müşteri Bilgileri")
        grp_cust.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        cust_layout = QFormLayout(grp_cust)
        cust_layout.setSpacing(10)

        # Otomatik Servis No
        self.le_service_no = QLineEdit()
        self.le_service_no.setReadOnly(True)
        if not self.record:
            self.le_service_no.setText(generate_service_no(self.session))
        cust_layout.addRow("Servis No:", self.le_service_no)

        # Kayıtlı Kişi Seçici (dialog_title parametresi kullanıldı)
        persons = self.session.query(Person).filter_by(is_active=True).order_by(Person.name.asc()).all()
        person_items = [(p.id, f"{p.name} ({p.phone})") for p in persons]
        self.cb_person = SearchableSelector(person_items, placeholder="Kayıtlı kişi ara veya seçin...", dialog_title="Kişi Seçin")
        self.cb_person.selectionChanged.connect(self._on_person_selected)
        cust_layout.addRow("Kayıtlı Kişi:", self.cb_person)

        self.le_cust_name = QLineEdit()
        self.le_cust_name.setPlaceholderText("Müşteri / Firma Adı Soyadı *")
        cust_layout.addRow("Ad Soyad *:", self.le_cust_name)

        self.le_cust_phone = QLineEdit()
        self.le_cust_phone.setPlaceholderText("05XX XXX XX XX")
        cust_layout.addRow("Telefon:", self.le_cust_phone)

        form_layout.addWidget(grp_cust)

        # ── Grup 2: Cihaz ve Arıza Bilgileri
        grp_device = QGroupBox("Cihaz ve Arıza Bilgileri")
        grp_device.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        dev_layout = QFormLayout(grp_device)
        dev_layout.setSpacing(10)

        self.le_device = QLineEdit()
        self.le_device.setPlaceholderText("Cihaz modeli, marka veya tanımı (örn: Asus Zenbook 14, PLC S7-1200)")
        dev_layout.addRow("Cihaz Bilgisi *:", self.le_device)

        self.le_device_serial = QLineEdit()
        self.le_device_serial.setPlaceholderText("Cihaz seri/IMEI numarası (opsiyonel)")
        dev_layout.addRow("Cihaz Seri No:", self.le_device_serial)

        self.te_complaint = QTextEdit()
        self.te_complaint.setMinimumHeight(100)
        self.te_complaint.setPlaceholderText("Müşterinin belirttiği arıza, şikayet ve talep detayları...")
        dev_layout.addRow("Şikayet / Arıza *:", self.te_complaint)

        self.cb_status = QComboBox()
        for s, _, _ in SERVICE_STATUSES:
            self.cb_status.addItem(s)
        dev_layout.addRow("Servis Durumu:", self.cb_status)

        form_layout.addWidget(grp_device)

        # ── Grup 3: Teslim & Kabul Bilgileri
        grp_delivery = QGroupBox("Teslim Bilgileri (Kayıt Aşaması)")
        grp_delivery.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        del_layout = QFormLayout(grp_delivery)
        del_layout.setSpacing(10)

        self.le_delivered_by = QLineEdit()
        self.le_delivered_by.setPlaceholderText("Cihazı servise teslim eden kişi (müşteri veya kurye)")
        del_layout.addRow("Teslim Eden:", self.le_delivered_by)

        self.le_received_by = QLineEdit()
        self.le_received_by.setText(self.user.full_name)
        self.le_received_by.setPlaceholderText("Cihazı teslim alan servis personeli")
        del_layout.addRow("Teslim Alan Personel:", self.le_received_by)

        self.te_notes = QTextEdit()
        self.te_notes.setMaximumHeight(80)
        self.te_notes.setPlaceholderText("Cihazla birlikte teslim alınan aksesuarlar (şarj aleti vb.) veya ek notlar...")
        del_layout.addRow("Ek Notlar:", self.te_notes)

        form_layout.addWidget(grp_delivery)

        scroll.setWidget(container)
        root_layout.addWidget(scroll)

        # Butonlar
        btns_layout = QHBoxLayout()
        btns_layout.addStretch()
        btn_cancel = btn("İptal", "danger", height=32)
        btn_cancel.clicked.connect(self.reject)
        btn_save = btn("💾 Kaydet", "success", height=32)
        btn_save.clicked.connect(self._save)
        btns_layout.addWidget(btn_cancel)
        btns_layout.addWidget(btn_save)
        root_layout.addLayout(btns_layout)

    def _on_person_selected(self, person_id):
        if not person_id:
            return
        p = self.session.query(Person).get(person_id)
        if p:
            self.le_cust_name.setText(p.name or "")
            self.le_cust_phone.setText(p.phone or "")
            if not self.le_delivered_by.text():
                self.le_delivered_by.setText(p.name or "")

    def _load(self):
        r = self.record
        self.le_service_no.setText(r.service_no)
        if r.person_id:
            self.cb_person.setSelectedId(r.person_id)
        self.le_cust_name.setText(r.customer_name or "")
        self.le_cust_phone.setText(r.customer_phone or "")
        self.le_device.setText(r.device_info or "")
        self.le_device_serial.setText(r.device_serial or "")
        self.te_complaint.setPlainText(r.complaint or "")
        self.cb_status.setCurrentText(r.status or "Kayıt Alındı")
        self.le_delivered_by.setText(r.delivered_by or "")
        self.le_received_by.setText(r.received_by or "")
        self.te_notes.setPlainText(r.notes or "")

    def _save(self):
        device = self.le_device.text().strip()
        complaint = self.te_complaint.toPlainText().strip()
        cust_name = self.le_cust_name.text().strip()

        if not device:
            QMessageBox.warning(self, "Uyarı", "Cihaz bilgisi zorunludur.")
            self.le_device.setFocus()
            return

        if not complaint:
            QMessageBox.warning(self, "Uyarı", "Şikayet / arıza açıklaması zorunludur.")
            self.te_complaint.setFocus()
            return

        if not cust_name:
            QMessageBox.warning(self, "Uyarı", "Müşteri adı zorunludur.")
            self.le_cust_name.setFocus()
            return

        try:
            is_new = False
            if not self.record:
                is_new = True
                self.record = ServiceRecord()
                self.record.service_no = self.le_service_no.text().strip()
                self.record.user_id = self.user.id
                self.session.add(self.record)

            old_status = self.record.status
            new_status = self.cb_status.currentText()

            self.record.person_id = self.cb_person.selectedId
            self.record.customer_name = cust_name
            self.record.customer_phone = self.le_cust_phone.text().strip() or None
            self.record.device_info = device
            self.record.device_serial = self.le_device_serial.text().strip() or None
            self.record.complaint = complaint
            self.record.status = new_status
            self.record.delivered_by = self.le_delivered_by.text().strip() or None
            self.record.received_by = self.le_received_by.text().strip() or None
            self.record.notes = self.te_notes.toPlainText().strip() or None

            self.session.flush()

            # Tarihçe logu oluştur
            if is_new:
                history = ServiceHistory(
                    service_id=self.record.id,
                    user_id=self.user.id,
                    old_status=None,
                    new_status=new_status,
                    notes="Yeni servis kaydı oluşturuldu."
                )
                self.session.add(history)
            elif old_status != new_status:
                history = ServiceHistory(
                    service_id=self.record.id,
                    user_id=self.user.id,
                    old_status=old_status,
                    new_status=new_status,
                    notes=f"Durum güncellendi: {old_status} → {new_status}"
                )
                self.session.add(history)

            self.session.commit()
            self.accept()
        except Exception as e:
            self.session.rollback()
            QMessageBox.critical(self, "Hata", f"Servis kaydı kaydedilirken hata oluştu:\n{e}")


# ─── Teslim Diyaloğu ─────────────────────────────────────────────────────────

class DeliveryDialog(QDialog):
    """Cihazın müşteriye teslim bilgilerini girmek için kullanılan diyalog."""

    def __init__(self, record, user, parent=None):
        super().__init__(parent)
        self.record = record
        self.user = user
        self.setWindowTitle(f"📦 Cihaz Teslim Bilgileri — {record.service_no}")
        self.setMinimumWidth(440)
        self._build_ui()

    def _build_ui(self):
        layout = QFormLayout(self)
        layout.setContentsMargins(22, 18, 22, 18)
        layout.setSpacing(12)

        title = QLabel("Cihaz Teslim İşlemi")
        title.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        title.setStyleSheet("color: #06b6d4;")
        layout.addRow(title)

        info = QLabel(f"Cihaz: <b>{self.record.device_info}</b><br>Müşteri: <b>{self.record.customer_name}</b>")
        info.setStyleSheet("color: #4a5568; font-size: 13px;")
        layout.addRow(info)

        self.le_delivered_to = QLineEdit()
        self.le_delivered_to.setText(self.record.customer_name or "")
        self.le_delivered_to.setPlaceholderText("Cihazı teslim alan kişi")
        layout.addRow("Teslim Edilen Kişi *:", self.le_delivered_to)

        self.le_received_from = QLineEdit()
        self.le_received_from.setText(self.user.full_name)
        self.le_received_from.setPlaceholderText("Cihazı teslim eden servis personeli")
        layout.addRow("Teslim Eden Personel *:", self.le_received_from)

        self.te_notes = QTextEdit()
        self.te_notes.setMaximumHeight(70)
        self.te_notes.setPlaceholderText("Teslim notu / açıklama (opsiyonel)...")
        layout.addRow("Teslim Notu:", self.te_notes)

        btns = QHBoxLayout()
        btns.addStretch()
        btn_cancel = btn("İptal", "secondary", height=30)
        btn_cancel.clicked.connect(self.reject)
        btn_ok = btn("Teslim Et", "success", height=30)
        btn_ok.clicked.connect(self._confirm)
        btns.addWidget(btn_cancel)
        btns.addWidget(btn_ok)
        layout.addRow(btns)

    def _confirm(self):
        if not self.le_delivered_to.text().strip():
            QMessageBox.warning(self, "Uyarı", "Teslim edilen kişi bilgisi zorunludur.")
            self.le_delivered_to.setFocus()
            return
        if not self.le_received_from.text().strip():
            QMessageBox.warning(self, "Uyarı", "Teslim eden personel bilgisi zorunludur.")
            self.le_received_from.setFocus()
            return
        self.accept()


# ─── Servis Detay Ekranı ─────────────────────────────────────────────────────

class ServiceDetailDialog(QDialog):
    """Servis detay görüntüleme — ürün ekleme, yapılan işlem ve durum yönetimi burada yapılır."""

    def __init__(self, session, user, record_id, parent=None):
        super().__init__(parent)
        self.session = session
        self.user = user
        self.record_id = record_id
        self.record = self.session.query(ServiceRecord).get(record_id)
        self.refresh_needed = False

        self.setWindowTitle(f"Servis Detayı — {self.record.service_no}")
        self.setMinimumSize(680, 500)
        maximize_dialog(self)
        self._build_ui()
        self._update_views()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(18, 16, 18, 16)
        root.setSpacing(12)

        # ── 1. Üst Başlık Banner
        header = QFrame()
        header.setStyleSheet("""
            background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #0f172a,stop:1 #1e3a5f);
            border-radius: 10px;
        """)
        hl = QHBoxLayout(header)
        hl.setContentsMargins(18, 12, 18, 12)

        left_col = QVBoxLayout()
        left_col.setSpacing(3)
        self.lbl_header_title = QLabel("")
        self.lbl_header_title.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        self.lbl_header_title.setStyleSheet("color: white; background: transparent;")

        self.lbl_header_sub = QLabel("")
        self.lbl_header_sub.setStyleSheet("color: #93c5fd; font-size: 12px; background: transparent;")
        left_col.addWidget(self.lbl_header_title)
        left_col.addWidget(self.lbl_header_sub)
        hl.addLayout(left_col)

        hl.addStretch()

        # Sağ: Durum Rozeti ve Butonlar
        right_col = QVBoxLayout()
        right_col.setAlignment(Qt.AlignmentFlag.AlignRight)
        right_col.setSpacing(6)

        self.lbl_badge = QLabel("")
        self.lbl_badge.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        self.lbl_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        right_col.addWidget(self.lbl_badge)

        btn_row = QHBoxLayout()
        if getattr(self.user.role, 'can_edit', True):
            btn_edit = btn("✏️ Düzenle", "secondary", height=28)
            btn_edit.clicked.connect(self._edit)
            btn_row.addWidget(btn_edit)

            self.btn_deliver = btn("📦 Teslim Et", "success", height=28)
            self.btn_deliver.clicked.connect(self._deliver)
            btn_row.addWidget(self.btn_deliver)

        right_col.addLayout(btn_row)
        hl.addLayout(right_col)
        root.addWidget(header)

        # ── 2. Scroll İçerik Alanı
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        container = QWidget()
        container.setStyleSheet("background: transparent;")
        clayout = QVBoxLayout(container)
        clayout.setSpacing(12)
        clayout.setContentsMargins(0, 0, 0, 0)

        # A) Şikayet & Teslim Kartı
        info_row = QHBoxLayout()
        info_row.setSpacing(12)

        # Şikayet Kutusu
        box_comp = QGroupBox("Müşteri Şikayeti / Arıza")
        box_comp.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        bcl = QVBoxLayout(box_comp)
        self.lbl_comp = QLabel("")
        self.lbl_comp.setWordWrap(True)
        self.lbl_comp.setStyleSheet("font-size: 13px; color: #1e293b; padding: 4px;")
        bcl.addWidget(self.lbl_comp)
        info_row.addWidget(box_comp, 3)

        # Teslim Bilgileri Kutusu
        box_del = QGroupBox("Teslim / Kabul Bilgileri")
        box_del.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        bdl = QFormLayout(box_del)
        bdl.setSpacing(6)
        self.lbl_deliv_by = QLabel("—")
        self.lbl_recv_by = QLabel("—")
        self.lbl_deliv_to = QLabel("—")
        self.lbl_recv_from = QLabel("—")
        bdl.addRow("Girişte Teslim Eden:", self.lbl_deliv_by)
        bdl.addRow("Girişte Teslim Alan:", self.lbl_recv_by)
        bdl.addRow("Çıkışta Teslim Alan:", self.lbl_deliv_to)
        bdl.addRow("Çıkışta Teslim Eden:", self.lbl_recv_from)
        info_row.addWidget(box_del, 2)

        clayout.addLayout(info_row)

        # B) Yapılan İşlem & Durum Yönetimi Kutusu
        grp_work = QGroupBox("Yapılan İşlem & Durum Güncelleme")
        grp_work.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        gwl = QVBoxLayout(grp_work)
        gwl.setSpacing(10)

        self.te_work_done = QTextEdit()
        self.te_work_done.setMinimumHeight(75)
        self.te_work_done.setPlaceholderText("Teknisyenin yaptığı onarım, bakım ve işlemler...")
        gwl.addWidget(self.te_work_done)

        work_btn_row = QHBoxLayout()
        work_btn_row.addWidget(QLabel("Servis Durumunu Güncelle:"))
        self.cb_status_update = QComboBox()
        for s, _, _ in SERVICE_STATUSES:
            self.cb_status_update.addItem(s)
        work_btn_row.addWidget(self.cb_status_update)

        btn_save_work = btn("💾 İşlemi ve Durumu Kaydet", "primary", height=30)
        btn_save_work.clicked.connect(self._save_work_done)
        work_btn_row.addWidget(btn_save_work)
        work_btn_row.addStretch()
        gwl.addLayout(work_btn_row)

        clayout.addWidget(grp_work)

        # C) Serviste Kullanılan Ürünler (Yedek Parça)
        grp_items = QGroupBox("Serviste Kullanılan Yedek Parçalar / Ürünler")
        grp_items.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        gil = QVBoxLayout(grp_items)
        gil.setSpacing(10)

        # Parça Ekleme Alanı
        if getattr(self.user.role, 'can_create', True) or getattr(self.user.role, 'can_edit', True):
            add_item_box = QFrame()
            add_item_box.setStyleSheet("background: #f1f5f9; border-radius: 6px; padding: 4px;")
            ail = QHBoxLayout(add_item_box)
            ail.setContentsMargins(8, 6, 8, 6)
            ail.setSpacing(8)

            # Depo Seçici
            warehouses = self.session.query(Warehouse).filter_by(is_active=True).all()
            self.cb_item_wh = QComboBox()
            for wh in warehouses:
                self.cb_item_wh.addItem(wh.name, wh.id)
            ail.addWidget(QLabel("Depo:"))
            ail.addWidget(self.cb_item_wh)

            # Ürün Seçici (dialog_title parametresi ile güvenli çağrı)
            products = self.session.query(Product).filter_by(is_active=True).order_by(Product.name.asc()).all()
            prod_items = [(p.id, f"{p.product_code} — {p.name}") for p in products]
            self.cb_item_product = SearchableSelector(prod_items, placeholder="Ürün ara veya seçin...", dialog_title="Ürün Seçin")
            ail.addWidget(QLabel("Ürün:"))
            ail.addWidget(self.cb_item_product, 2)

            # Miktar
            self.spin_item_qty = QDoubleSpinBox()
            self.spin_item_qty.setRange(0.01, 10000)
            self.spin_item_qty.setValue(1.0)
            self.spin_item_qty.setFixedWidth(75)
            ail.addWidget(QLabel("Miktar:"))
            ail.addWidget(self.spin_item_qty)

            btn_add_part = btn("+ Ürün Ekle", "success", height=28)
            btn_add_part.clicked.connect(self._add_item)
            ail.addWidget(btn_add_part)

            gil.addWidget(add_item_box)

        # Kullanılan Parçalar Tablosu
        self.items_table = QTableWidget()
        self.items_table.setColumnCount(7)
        self.items_table.setHorizontalHeaderLabels([
            "ID", "Ürün Kodu", "Ürün Adı", "Depo", "Miktar", "Seri Numaraları", "İşlem"
        ])
        ih = self.items_table.horizontalHeader()
        ih.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        ih.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        ih.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        ih.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        ih.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        ih.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        ih.setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)
        ih.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)
        self.items_table.verticalHeader().setVisible(False)
        self.items_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.items_table.setAlternatingRowColors(True)
        self.items_table.setMinimumHeight(130)
        gil.addWidget(self.items_table)

        clayout.addWidget(grp_items)

        # D) Durum Tarihçesi
        grp_hist = QGroupBox("Durum Tarihçesi")
        grp_hist.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        ghl = QVBoxLayout(grp_hist)

        self.hist_table = QTableWidget()
        self.hist_table.setColumnCount(4)
        self.hist_table.setHorizontalHeaderLabels(["Tarih", "İşlemi Yapan", "Durum Değişimi", "Açıklama / Not"])
        hh = self.hist_table.horizontalHeader()
        hh.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        hh.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.hist_table.verticalHeader().setVisible(False)
        self.hist_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.hist_table.setAlternatingRowColors(True)
        self.hist_table.setMinimumHeight(120)
        ghl.addWidget(self.hist_table)

        clayout.addWidget(grp_hist)

        scroll.setWidget(container)
        root.addWidget(scroll)

        # Alt Buton
        bottom_bar = QHBoxLayout()
        bottom_bar.addStretch()
        btn_close = btn("Kapat", "secondary", height=30, width=90)
        btn_close.clicked.connect(self.accept if self.refresh_needed else self.reject)
        bottom_bar.addWidget(btn_close)
        root.addLayout(bottom_bar)

    def _update_views(self):
        """Arayüzü sıfırlamadan verileri yerinde günceller (çökme ve titremeyi önler)."""
        r = self.record
        status_color, status_bg = STATUS_COLOR_MAP.get(r.status, ("#64748b", "#f1f5f9"))

        # Banner başlıkları
        self.lbl_header_title.setText(f"{r.service_no} — {r.device_info}")
        cust_info = f"Müşteri: <b>{r.customer_name or '—'}</b>"
        if r.customer_phone:
            cust_info += f" &nbsp;|&nbsp; Tel: <b>{r.customer_phone}</b>"
        if r.device_serial:
            cust_info += f" &nbsp;|&nbsp; Seri No: <b>{r.device_serial}</b>"
        self.lbl_header_sub.setText(cust_info)

        # Rozet
        self.lbl_badge.setText(f"  {r.status}  ")
        self.lbl_badge.setStyleSheet(f"""
            background: {status_bg};
            color: {status_color};
            border: 1.5px solid {status_color};
            border-radius: 6px;
            padding: 3px 10px;
        """)

        # Teslim Et Butonu Görünürlüğü
        if hasattr(self, 'btn_deliver'):
            self.btn_deliver.setVisible(r.status != "Teslim Edildi")

        # Şikayet ve Teslim Kartı
        self.lbl_comp.setText(r.complaint or "—")
        self.lbl_deliv_by.setText(r.delivered_by or "—")
        self.lbl_recv_by.setText(r.received_by or "—")
        self.lbl_deliv_to.setText(r.delivered_to or "—")
        self.lbl_recv_from.setText(r.received_from or "—")

        # Yapılan İşlem ve Durum
        self.te_work_done.setPlainText(r.work_done or "")
        self.cb_status_update.setCurrentText(r.status)

        # Tablolar
        self._refresh_items_table()
        self._refresh_history_table()

    def _refresh_items_table(self):
        self.items_table.setRowCount(len(self.record.items))
        for row, item in enumerate(self.record.items):
            self.items_table.setRowHeight(row, 34)

            p = item.product
            wh = item.warehouse

            # ID
            item_id = QTableWidgetItem(str(item.id))
            item_id.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.items_table.setItem(row, 0, item_id)

            # Ürün Kodu & Adı
            self.items_table.setItem(row, 1, QTableWidgetItem(p.product_code if p else "—"))
            self.items_table.setItem(row, 2, QTableWidgetItem(p.name if p else "—"))

            # Depo
            self.items_table.setItem(row, 3, QTableWidgetItem(wh.name if wh else "—"))

            # Miktar
            qty_text = f"{item.quantity:.2f}".rstrip("0").rstrip(".") + f" {p.unit if p else ''}"
            item_qty = QTableWidgetItem(qty_text)
            item_qty.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.items_table.setItem(row, 4, item_qty)

            # Seri No
            self.items_table.setItem(row, 5, QTableWidgetItem(item.serial_number or "—"))

            # İşlemler
            btn_cell = QWidget()
            b_layout = QHBoxLayout(btn_cell)
            b_layout.setContentsMargins(2, 2, 2, 2)
            if getattr(self.user.role, 'can_delete', True):
                b_del = btn("Kaldır", "danger", height=26, width=75)
                b_del.clicked.connect(lambda _, it=item: self._remove_item(it))
                b_layout.addWidget(b_del)
            self.items_table.setCellWidget(row, 6, btn_cell)

    def _refresh_history_table(self):
        histories = self.session.query(ServiceHistory).filter_by(
            service_id=self.record.id
        ).order_by(ServiceHistory.created_at.desc()).all()

        self.hist_table.setRowCount(len(histories))
        for row, h in enumerate(histories):
            self.hist_table.setRowHeight(row, 32)

            # Tarih
            dt_str = h.created_at.strftime("%d.%m.%Y %H:%M") if h.created_at else "—"
            item_dt = QTableWidgetItem(dt_str)
            item_dt.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.hist_table.setItem(row, 0, item_dt)

            # İşlemi Yapan
            u_name = h.user.full_name if h.user else "Sistem"
            self.hist_table.setItem(row, 1, QTableWidgetItem(u_name))

            # Durum Değişimi
            trans = f"{h.old_status or 'Başlangıç'} → {h.new_status}"
            item_tr = QTableWidgetItem(trans)
            item_tr.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            self.hist_table.setItem(row, 2, item_tr)

            # Açıklama
            self.hist_table.setItem(row, 3, QTableWidgetItem(h.notes or "—"))

    def _add_item(self):
        prod_id = self.cb_item_product.selectedId
        if not prod_id:
            QMessageBox.warning(self, "Uyarı", "Lütfen bir ürün seçin.")
            return

        wh_id = self.cb_item_wh.currentData()
        if not wh_id:
            QMessageBox.warning(self, "Uyarı", "Lütfen bir depo seçin.")
            return

        qty = self.spin_item_qty.value()
        if qty <= 0:
            QMessageBox.warning(self, "Uyarı", "Miktar 0'dan büyük olmalıdır.")
            return

        product = self.session.query(Product).get(prod_id)
        current_stock = get_stock_level(self.session, prod_id, wh_id)

        if current_stock < qty:
            QMessageBox.warning(
                self, "Yetersiz Stok",
                f"Seçilen depoda yeterli stok bulunmuyor!\n"
                f"Mevcut Stok: {current_stock:.2f} {product.unit}\n"
                f"İstenen: {qty:.2f} {product.unit}"
            )
            return

        selected_serials = []
        if product.serial_tracking:
            if not qty.is_integer():
                QMessageBox.warning(self, "Uyarı", "Seri numaralı ürünlerde miktar tam sayı olmalıdır.")
                return

            available_serials = get_available_serials(self.session, prod_id, wh_id)
            if len(available_serials) < int(qty):
                QMessageBox.warning(
                    self, "Yetersiz Seri Numarası",
                    f"Bu depoda kullanılabilir yalnızca {len(available_serials)} adet seri numarası bulunmaktadır."
                )
                return

            dlg = SerialSelectDialog(product.name, available_serials, int(qty), parent=self)
            if dlg.exec() != QDialog.DialogCode.Accepted:
                return
            selected_serials = dlg.selected_serials

        try:
            # 1. Stok hareketi oluştur (SERVICE_OUT)
            movement = StockMovement(
                product_id=prod_id,
                warehouse_id=wh_id,
                movement_type="SERVICE_OUT",
                quantity=qty,
                serial_numbers_json=selected_serials if selected_serials else None,
                reason=f"Servis: {self.record.service_no} — {self.record.device_info}",
                reference_id=self.record.id,
                reference_type="SERVICE",
                user_id=self.user.id
            )
            self.session.add(movement)
            self.session.flush()

            # 2. Seri numaralarını 'used' olarak işaretle
            if selected_serials:
                for s_no in selected_serials:
                    sn_obj = self.session.query(SerialNumber).filter_by(
                        product_id=prod_id,
                        warehouse_id=wh_id,
                        serial_no=s_no,
                        status="available"
                    ).first()
                    if sn_obj:
                        sn_obj.status = "used"

            # 3. ServiceItem kaydı oluştur
            serials_str = ", ".join(selected_serials) if selected_serials else None
            item = ServiceItem(
                service_id=self.record.id,
                product_id=prod_id,
                warehouse_id=wh_id,
                quantity=qty,
                serial_number=serials_str,
                stock_movement_id=movement.id
            )
            self.session.add(item)
            self.session.commit()

            self.refresh_needed = True
            self.session.refresh(self.record)
            self._update_views()
            QMessageBox.information(self, "Başarılı", f"{product.name} ({qty:.2f} {product.unit}) servise eklendi.")
        except Exception as e:
            self.session.rollback()
            QMessageBox.critical(self, "Hata", f"Ürün servise eklenirken hata oluştu:\n{e}")

    def _remove_item(self, item):
        reply = QMessageBox.question(
            self, "Onay",
            f"'{item.product.name}' parçasını servis kaydından kaldırmak ve stoğa iade etmek istediğinize emin misiniz?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        try:
            # Seri numaraları varsa tekrar 'available' yap
            if item.serial_number:
                serials = [s.strip() for s in item.serial_number.split(",") if s.strip()]
                for s_no in serials:
                    sn_obj = self.session.query(SerialNumber).filter_by(
                        product_id=item.product_id,
                        serial_no=s_no
                    ).first()
                    if sn_obj:
                        sn_obj.status = "available"
                        sn_obj.warehouse_id = item.warehouse_id

            # İlgili stok hareketini sil
            if item.stock_movement_id:
                m = self.session.query(StockMovement).get(item.stock_movement_id)
                if m:
                    self.session.delete(m)

            self.session.delete(item)
            self.session.commit()

            self.refresh_needed = True
            self.session.refresh(self.record)
            self._update_views()
            QMessageBox.information(self, "Başarılı", "Ürün servis kaydından kaldırıldı ve stoğa iade edildi.")
        except Exception as e:
            self.session.rollback()
            QMessageBox.critical(self, "Hata", f"Ürün kaldırılırken hata oluştu:\n{e}")

    def _save_work_done(self):
        work = self.te_work_done.toPlainText().strip()
        new_status = self.cb_status_update.currentText()
        old_status = self.record.status

        try:
            self.record.work_done = work or None

            if old_status != new_status:
                self.record.status = new_status
                hist = ServiceHistory(
                    service_id=self.record.id,
                    user_id=self.user.id,
                    old_status=old_status,
                    new_status=new_status,
                    notes=f"Durum güncellendi: {old_status} → {new_status}"
                )
                self.session.add(hist)

            self.session.commit()
            self.refresh_needed = True
            self.session.refresh(self.record)
            self._update_views()
            QMessageBox.information(self, "Başarılı", "Yapılan işlem ve durum kaydedildi.")
        except Exception as e:
            self.session.rollback()
            QMessageBox.critical(self, "Hata", f"İşlem kaydedilirken hata oluştu:\n{e}")

    def _edit(self):
        dlg = ServiceFormDialog(self.session, self.user, record=self.record, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.refresh_needed = True
            self.session.refresh(self.record)
            self._update_views()

    def _deliver(self):
        dlg = DeliveryDialog(self.record, self.user, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            old_status = self.record.status
            self.record.delivered_to = dlg.le_delivered_to.text().strip()
            self.record.received_from = dlg.le_received_from.text().strip()
            self.record.status = "Teslim Edildi"

            deliv_note = dlg.te_notes.toPlainText().strip()
            notes_text = f"Cihaz teslim edildi. Teslim Alan: {self.record.delivered_to}, Teslim Eden: {self.record.received_from}"
            if deliv_note:
                notes_text += f" | Not: {deliv_note}"

            hist = ServiceHistory(
                service_id=self.record.id,
                user_id=self.user.id,
                old_status=old_status,
                new_status="Teslim Edildi",
                notes=notes_text
            )
            self.session.add(hist)
            self.session.commit()

            self.refresh_needed = True
            self.session.refresh(self.record)
            self._update_views()
            QMessageBox.information(self, "Başarılı", "Cihaz teslim edildi olarak işaretlendi.")


# ─── Teknik Servis Ana Sayfası ───────────────────────────────────────────────

class ServicePage(QWidget):
    def __init__(self, session, user):
        super().__init__()
        self.session = session
        self.user = user
        self._all = []
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(12)

        # ── 1. Üst İstatistik Kartları (Duyarlı / Responsive)
        self.stats_layout = QHBoxLayout()
        self.stats_layout.setSpacing(10)
        self.stat_labels = {}

        stat_cards = [
            ("total", "Toplam Servis", "#2563eb", "#eff6ff"),
            ("received", "Kayıt / İnceleme", "#f59e0b", "#fffbeb"),
            ("repairing", "Onayda / Onarıldı", "#10b981", "#ecfdf5"),
            ("delivered", "Teslim Edildi", "#06b6d4", "#ecfeff"),
        ]

        for key, title, color, bg in stat_cards:
            card = QFrame()
            card.setStyleSheet(f"""
                QFrame {{
                    background: {bg};
                    border: 1.5px solid {color}30;
                    border-radius: 8px;
                }}
            """)
            cl = QVBoxLayout(card)
            cl.setContentsMargins(12, 10, 12, 10)
            cl.setSpacing(2)

            val_lbl = QLabel("0")
            val_lbl.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
            val_lbl.setStyleSheet(f"color: {color}; background: transparent;")
            val_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

            name_lbl = QLabel(title)
            name_lbl.setStyleSheet("color: #64748b; font-size: 11px; font-weight: 600; background: transparent;")
            name_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

            cl.addWidget(val_lbl)
            cl.addWidget(name_lbl)
            self.stats_layout.addWidget(card)
            self.stat_labels[key] = val_lbl

        layout.addLayout(self.stats_layout)

        # ── 2. Arama ve Filtre Çubuğu
        filter_bar = QHBoxLayout()
        filter_bar.setSpacing(10)

        self.le_search = QLineEdit()
        self.le_search.setPlaceholderText("🔍 Servis no, cihaz, müşteri, telefon ara...")
        self.le_search.setMinimumWidth(220)
        self.le_search.textChanged.connect(self._filter)
        filter_bar.addWidget(self.le_search)

        self.cb_status_filter = QComboBox()
        self.cb_status_filter.addItem("Tüm Durumlar")
        for s, _, _ in SERVICE_STATUSES:
            self.cb_status_filter.addItem(s)
        self.cb_status_filter.currentIndexChanged.connect(self._filter)
        filter_bar.addWidget(self.cb_status_filter)

        filter_bar.addStretch()

        btn_refresh = btn("Yenile", "secondary", height=30)
        btn_refresh.clicked.connect(self.refresh)
        filter_bar.addWidget(btn_refresh)

        if getattr(self.user.role, 'can_create', True):
            btn_new = btn("+ Yeni Servis", "primary", height=30)
            btn_new.clicked.connect(self._new_service)
            filter_bar.addWidget(btn_new)

        layout.addLayout(filter_bar)

        # ── 3. Servis Kayıtları Tablosu (Duyarlı Kolon Boyutları)
        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            "Servis No", "Müşteri", "Telefon", "Cihaz / Model", "Şikayet / Arıza", "Durum", "Kayıt Tarihi", "İşlemler"
        ])
        
        hh = self.table.horizontalHeader()
        hh.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        hh.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents) # Servis No
        hh.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents) # Müşteri
        hh.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents) # Telefon
        hh.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)          # Cihaz / Model
        hh.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)          # Şikayet
        hh.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents) # Durum
        hh.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents) # Tarih
        hh.setSectionResizeMode(7, QHeaderView.ResizeMode.ResizeToContents) # İşlemler
        
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.doubleClicked.connect(lambda idx: self._open_detail(self._get_current_records()[idx.row()]))
        layout.addWidget(self.table)

        tip = QLabel("💡 Satıra çift tıklayarak veya 'Detay' butonuna basarak servis detay ve işlem ekranını açabilirsiniz.")
        tip.setStyleSheet("color: #94a3b8; font-size: 11px;")
        layout.addWidget(tip)

    def refresh(self):
        self._all = self.session.query(ServiceRecord).order_by(ServiceRecord.created_at.desc()).all()
        self._update_stats()
        self._filter()

    def _update_stats(self):
        total = len(self._all)
        received = sum(1 for r in self._all if r.status in ("Kayıt Alındı", "İncelemede"))
        repairing = sum(1 for r in self._all if r.status in ("Onay Bekliyor", "Onarıldı"))
        delivered = sum(1 for r in self._all if r.status == "Teslim Edildi")

        self.stat_labels["total"].setText(str(total))
        self.stat_labels["received"].setText(str(received))
        self.stat_labels["repairing"].setText(str(repairing))
        self.stat_labels["delivered"].setText(str(delivered))

    def _filter(self):
        txt = self.le_search.text().strip()
        status_filter = self.cb_status_filter.currentText()

        records = self._all

        if status_filter != "Tüm Durumlar":
            records = [r for r in records if r.status == status_filter]

        if txt:
            records = [
                r for r in records
                if tr_contains(txt, r.service_no)
                or tr_contains(txt, r.customer_name)
                or tr_contains(txt, r.customer_phone)
                or tr_contains(txt, r.device_info)
                or tr_contains(txt, r.complaint)
                or tr_contains(txt, r.device_serial)
            ]

        self._populate(records)

    def _populate(self, records):
        self._current_shown = records
        self.table.setRowCount(len(records))

        for row, r in enumerate(records):
            self.table.setRowHeight(row, 38)

            # Servis No
            item_no = QTableWidgetItem(r.service_no)
            item_no.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            item_no.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 0, item_no)

            # Müşteri
            self.table.setItem(row, 1, QTableWidgetItem(r.customer_name or "—"))

            # Telefon
            item_phone = QTableWidgetItem(r.customer_phone or "—")
            item_phone.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 2, item_phone)

            # Cihaz
            self.table.setItem(row, 3, QTableWidgetItem(r.device_info or "—"))

            # Şikayet
            comp_short = (r.complaint[:45] + "...") if r.complaint and len(r.complaint) > 45 else (r.complaint or "—")
            self.table.setItem(row, 4, QTableWidgetItem(comp_short))

            # Durum Rozeti
            color, bg = STATUS_COLOR_MAP.get(r.status, ("#64748b", "#f1f5f9"))
            status_item = QTableWidgetItem(r.status)
            status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            status_item.setForeground(QColor(color))
            status_item.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            self.table.setItem(row, 5, status_item)

            # Tarih
            dt_str = r.created_at.strftime("%d.%m.%Y") if r.created_at else "—"
            item_date = QTableWidgetItem(dt_str)
            item_date.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 6, item_date)

            # İşlemler Butonu
            btn_cell = QWidget()
            b_layout = QHBoxLayout(btn_cell)
            b_layout.setContentsMargins(3, 3, 3, 3)
            b_detail = btn("Detay", "primary", height=26, width=80)
            b_detail.clicked.connect(lambda _, rec=r: self._open_detail(rec))
            b_layout.addWidget(b_detail)
            self.table.setCellWidget(row, 7, btn_cell)

    def _get_current_records(self):
        return getattr(self, "_current_shown", self._all)

    def _new_service(self):
        dlg = ServiceFormDialog(self.session, self.user, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.refresh()
            if dlg.record:
                self._open_detail_by_id(dlg.record.id)

    def _open_detail(self, record):
        if not record:
            return
        self._open_detail_by_id(record.id)

    def _open_detail_by_id(self, record_id):
        dlg = ServiceDetailDialog(self.session, self.user, record_id, parent=self)
        dlg.exec()
        self.refresh()
