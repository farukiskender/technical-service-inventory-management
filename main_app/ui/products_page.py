"""
Ürün Yönetimi Modülü — Ürün listesi ve form
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QDialog, QFormLayout,
    QLineEdit, QCheckBox, QComboBox, QTextEdit, QHeaderView,
    QMessageBox, QDialogButtonBox, QFrame, QFileDialog
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QFont, QColor, QPixmap
import shutil

from shared.schema import Product
from shared.utils import tr_contains
from main_app.ui.stock_page import btn, maximize_dialog


UNITS = ["Adet", "Metre", "Litre", "Gram", "Kilogram", "Kutu", "Paket", "Rulo", "Çift"]
CATEGORIES = ["Elektronik", "Mekanik", "Sarf Malzeme", "Aksesuar", "Yedek Parça", "Diğer"]


class ProductDialog(QDialog):
    def __init__(self, session, user, product=None, parent=None):
        super().__init__(parent)
        self.session = session
        self.user = user
        self.product = product
        self.setWindowTitle("Ürün Ekle" if not product else "Ürün Düzenle")
        self.setMinimumWidth(450)
        maximize_dialog(self)
        self.current_image_path = None
        self._build_ui()
        if product:
            self._load()

    def _build_ui(self):
        layout = QFormLayout(self)
        layout.setContentsMargins(25, 25, 25, 20)
        layout.setSpacing(13)

        title = QLabel("Ürün Bilgileri")
        title.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        title.setStyleSheet("color: #2b6cb0; margin-bottom: 5px;")
        layout.addRow(title)

        self.le_name = QLineEdit()
        self.le_name.setPlaceholderText("Ürün adı")
        self.cb_category = QComboBox()
        self.cb_category.setEditable(True)
        self.cb_category.addItems([""] + CATEGORIES)
        self.cb_unit = QComboBox()
        self.cb_unit.addItems(UNITS)
        self.te_desc = QTextEdit()
        self.te_desc.setMaximumHeight(80)
        self.te_desc.setPlaceholderText("Açıklama (opsiyonel)")
        self.chk_serial = QCheckBox("Seri numarası takibi aktif")
        self.chk_active = QCheckBox("Aktif")
        self.chk_active.setChecked(True)

        layout.addRow("Ürün Adı *:", self.le_name)
        layout.addRow("Kategori:", self.cb_category)
        layout.addRow("Birim:", self.cb_unit)
        layout.addRow("Açıklama:", self.te_desc)
        
        # Görsel Yükleme
        img_layout = QHBoxLayout()
        self.lbl_img_preview = QLabel("Görsel Yok")
        self.lbl_img_preview.setFixedSize(100, 100)
        self.lbl_img_preview.setStyleSheet("border: 1px dashed #cbd5e1; color: #94a3b8;")
        self.lbl_img_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        btn_img_select = btn("Görsel Seç", "secondary", height=28)
        btn_img_select.clicked.connect(self._select_image)
        
        img_layout.addWidget(self.lbl_img_preview)
        img_layout.addWidget(btn_img_select)
        img_layout.addStretch()
        layout.addRow("Görsel:", img_layout)
        
        layout.addRow("", self.chk_serial)
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
        p = self.product
        self.le_name.setText(p.name)
        idx = self.cb_category.findText(p.category or "")
        if idx >= 0:
            self.cb_category.setCurrentIndex(idx)
        idx2 = self.cb_unit.findText(p.unit or "Adet")
        if idx2 >= 0:
            self.cb_unit.setCurrentIndex(idx2)
        self.te_desc.setPlainText(p.description or "")
        self.chk_serial.setChecked(bool(p.serial_tracking))
        self.chk_active.setChecked(bool(p.is_active))
        if p.image_path and os.path.exists(p.image_path):
            self.current_image_path = p.image_path
            pixmap = QPixmap(p.image_path).scaled(100, 100, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            self.lbl_img_preview.setPixmap(pixmap)
            self.lbl_img_preview.setText("")

    def _select_image(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Görsel Seç", "", "Resim Dosyaları (*.png *.jpg *.jpeg *.bmp)"
        )
        if file_path:
            self.current_image_path = file_path
            pixmap = QPixmap(file_path).scaled(100, 100, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            self.lbl_img_preview.setPixmap(pixmap)
            self.lbl_img_preview.setText("")

    def _generate_product_code(self):
        last = self.session.query(Product).order_by(Product.id.desc()).first()
        next_id = (last.id + 1) if last else 1
        return f"URN-{next_id:06d}"

    def _save(self):
        name = self.le_name.text().strip()
        if not name:
            QMessageBox.warning(self, "Uyarı", "Ürün adı zorunludur.")
            return
        try:
            if self.product:
                p = self.product
            else:
                p = Product()
                p.product_code = self._generate_product_code()
                self.session.add(p)
            p.name = name
            p.category = self.cb_category.currentText() or None
            p.unit = self.cb_unit.currentText()
            p.description = self.te_desc.toPlainText().strip() or None
            p.serial_tracking = self.chk_serial.isChecked()
            p.is_active = self.chk_active.isChecked()
            
            # Görsel Kaydetme İşlemi
            if self.current_image_path and self.current_image_path != getattr(p, 'image_path', None):
                images_dir = os.path.join(os.path.dirname(__file__), "../../shared/images")
                os.makedirs(images_dir, exist_ok=True)
                ext = os.path.splitext(self.current_image_path)[1]
                new_filename = f"{p.product_code}{ext}"
                dest_path = os.path.abspath(os.path.join(images_dir, new_filename))
                
                # Eğer seçilen resim zaten dest_path değilse kopyala
                if os.path.abspath(self.current_image_path) != dest_path:
                    shutil.copy(self.current_image_path, dest_path)
                
                p.image_path = dest_path

            self.session.commit()
            self.accept()
        except Exception as e:
            self.session.rollback()
            QMessageBox.critical(self, "Hata", str(e))


class ProductsPage(QWidget):
    def __init__(self, session, user):
        super().__init__()
        self.session = session
        self.user = user
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 15, 20, 15)
        layout.setSpacing(12)

        # Title bar
        top = QHBoxLayout()
        title = QLabel("Ürün Tanımları")
        title.setFont(QFont("Segoe UI", 15, QFont.Weight.Bold))
        title.setStyleSheet("color: #2d3748;")
        top.addWidget(title)
        top.addStretch()

        self.le_search = QLineEdit()
        self.le_search.setPlaceholderText("🔍 Ürün ara...")
        self.le_search.setFixedWidth(220)
        self.le_search.textChanged.connect(self._filter)
        top.addWidget(self.le_search)

        if self.user.role.can_create:
            btn_add = btn("+ Yeni Ürün", "success")
            btn_add.clicked.connect(self._add)
            top.addWidget(btn_add)

        layout.addLayout(top)

        # Stats
        self.stats_label = QLabel("")
        self.stats_label.setStyleSheet("color: #718096; font-size: 12px;")
        layout.addWidget(self.stats_label)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels(["Kod", "Ad", "Açıklama", "Kategori", "Birim", "Seri Takip", "Durum", "İşlem"])
        hh = self.table.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        hh.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        hh.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(7, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        layout.addWidget(self.table)

    def refresh(self):
        self._all_products = self.session.query(Product).order_by(Product.id.desc()).all()
        self._populate(self._all_products)

    def _filter(self):
        q = self.le_search.text().strip()
        if not q:
            self._populate(self._all_products)
            return
        filtered = [p for p in self._all_products
                    if tr_contains(q, p.name) or tr_contains(q, p.product_code)
                    or tr_contains(q, p.category)]
        self._populate(filtered)

    def _populate(self, products):
        self.table.setRowCount(len(products))
        total = len(self._all_products) if hasattr(self, '_all_products') else len(products)
        active = sum(1 for p in (self._all_products if hasattr(self, '_all_products') else products) if p.is_active)
        self.stats_label.setText(f"Toplam: {total} ürün  |  Aktif: {active}")

        for i, p in enumerate(products):
            self.table.setItem(i, 0, QTableWidgetItem(p.product_code or ""))
            self.table.setItem(i, 1, QTableWidgetItem(p.name))
            self.table.setItem(i, 2, QTableWidgetItem(p.description or ""))
            self.table.setItem(i, 3, QTableWidgetItem(p.category or ""))
            self.table.setItem(i, 4, QTableWidgetItem(p.unit or ""))

            serial_item = QTableWidgetItem("✓ Evet" if p.serial_tracking else "—")
            serial_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            serial_item.setForeground(QColor("#3182ce") if p.serial_tracking else QColor("#a0aec0"))
            self.table.setItem(i, 5, serial_item)

            status_item = QTableWidgetItem("Aktif" if p.is_active else "Pasif")
            status_item.setForeground(QColor("#38a169") if p.is_active else QColor("#e53e3e"))
            self.table.setItem(i, 6, status_item)

            btn_frame = QFrame()
            btn_layout = QHBoxLayout(btn_frame)
            btn_layout.setContentsMargins(4, 2, 4, 2)
            btn_layout.setSpacing(4)

            if self.user.role.can_edit:
                btn_edit = btn("Düzenle", "primary", height=28, width=90)
                btn_edit.clicked.connect(lambda _, pid=p.id: self._edit(pid))
                btn_layout.addWidget(btn_edit)

            if self.user.role.can_delete:
                variant = "danger" if p.is_active else "success"
                label = "Pasifleştir" if p.is_active else "Aktifleştir"
                btn_toggle = btn(label, variant, height=28, width=95)
                btn_toggle.clicked.connect(lambda _, pid=p.id: self._toggle(pid))
                btn_layout.addWidget(btn_toggle)

            self.table.setCellWidget(i, 7, btn_frame)
            self.table.setRowHeight(i, 38)

    def _add(self):
        dlg = ProductDialog(self.session, self.user, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.refresh()

    def _edit(self, pid):
        p = self.session.get(Product, pid)
        dlg = ProductDialog(self.session, self.user, product=p, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.refresh()

    def _toggle(self, pid):
        p = self.session.get(Product, pid)
        p.is_active = not p.is_active
        self.session.commit()
        self.refresh()
