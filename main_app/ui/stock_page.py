"""
Stok Yönetimi — Stok durumu, giriş/çıkış, depo transferi ve seri no takibi
+ Paylaşılan UI yardımcıları (btn, SearchableSelector)
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from datetime import datetime
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QDialog, QFormLayout,
    QLineEdit, QComboBox, QHeaderView, QMessageBox,
    QDialogButtonBox, QDoubleSpinBox, QTabWidget, QFrame, QTextEdit,
    QListWidget, QListWidgetItem, QAbstractItemView, QSplitter, QGroupBox,
    QCompleter, QScrollArea
)
from PyQt6.QtCore import Qt, pyqtSignal, QStringListModel
from PyQt6.QtGui import QFont, QColor

from shared.schema import Product, Warehouse, StockMovement, SerialNumber
from shared.utils import tr_contains


# ─── Buton yardımcısı (objectName yerine doğrudan stil) ──────────────────────

def btn(text, variant="primary", height=36, width=None):
    colors = {
        "primary":   ("#3182ce", "#2b6cb0"),
        "success":   ("#38a169", "#2f855a"),
        "danger":    ("#e53e3e", "#c53030"),
        "warning":   ("#d69e2e", "#b7791f"),
        "secondary": ("#718096", "#4a5568"),
    }
    bg, hv = colors.get(variant, colors["primary"])
    b = QPushButton(text)
    b.setMinimumHeight(height)
    if width:
        b.setFixedWidth(width)
    pad_h = 8 if (width and width < 100) else 14
    b.setStyleSheet(f"""
        QPushButton {{
            background-color: {bg};
            color: white;
            border: none;
            border-radius: 6px;
            padding: 0 {pad_h}px;
            font-weight: 600;
            font-size: 12px;
        }}
        QPushButton:hover {{ background-color: {hv}; }}
        QPushButton:pressed {{ background-color: {hv}; }}
    """)
    return b


# ─── Standart Boyutlu Dialog Yardımcısı ──────────────────────────────────────

def maximize_dialog(dialog):
    """Dialog'u standart boyutta ekranın ortasına yerleştirir (tam ekran yerine)."""
    from PyQt6.QtWidgets import QApplication
    screen = QApplication.primaryScreen()
    if screen:
        geom = screen.availableGeometry()
        w = int(geom.width() * 0.65)
        h = int(geom.height() * 0.75)
        # Minimum ve maksimum sınırlar
        w = max(750, min(w, 1200))
        h = max(550, min(h, 850))
        dialog.resize(w, h)
        # Ekranın ortasına konumlandır
        x = geom.x() + (geom.width() - w) // 2
        y = geom.y() + (geom.height() - h) // 2
        dialog.move(x, y)
    else:
        dialog.resize(900, 650)
    # Görsel iyileştirme
    dialog.setStyleSheet(dialog.styleSheet() + """
        QDialog {
            background: #f8fafc;
        }
    """)



# ─── Aramalı Seçici Widget ────────────────────────────────────────────────────

class SearchableListDialog(QDialog):
    """Tam liste görünümüyle aranabilir seçim diyaloğu"""

    def __init__(self, items, title="Seçim Yapın", columns=None, parent=None):
        """
        items: list of (id, display_text) tuples, veya list of (id, col1, col2, ...) tuples
        columns: sütun başlıkları listesi (None ise tek sütun)
        """
        super().__init__(parent)
        self.items = items
        self.selected_id = None
        self.setWindowTitle(title)
        self.setMinimumSize(600, 500)
        maximize_dialog(self)
        self._build_ui(columns)

    def _build_ui(self, columns):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 15, 20, 15)
        layout.setSpacing(12)

        # Arama
        search_row = QHBoxLayout()
        self.le_search = QLineEdit()
        self.le_search.setPlaceholderText("🔍 Ara...")
        self.le_search.setMinimumHeight(38)
        self.le_search.textChanged.connect(self._filter)
        search_row.addWidget(self.le_search)
        layout.addLayout(search_row)

        self.lbl_count = QLabel("")
        self.lbl_count.setStyleSheet("color: #718096; font-size: 12px;")
        layout.addWidget(self.lbl_count)

        # Tablo
        if columns:
            col_count = len(columns)
        else:
            col_count = 1
            columns = ["Seçenek"]

        self.table = QTableWidget()
        self.table.setColumnCount(col_count)
        self.table.setHorizontalHeaderLabels(columns)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.doubleClicked.connect(self._select_row)
        layout.addWidget(self.table)

        self._populate(self.items)

        # Butonlar
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_cancel = btn("İptal", "secondary")
        btn_cancel.clicked.connect(self.reject)
        btn_ok = btn("✓ Seç", "success")
        btn_ok.clicked.connect(self._confirm)
        btn_row.addWidget(btn_cancel)
        btn_row.addWidget(btn_ok)
        layout.addLayout(btn_row)

    def _populate(self, items):
        self.table.setRowCount(len(items))
        for i, item_data in enumerate(items):
            if isinstance(item_data, (list, tuple)):
                # İlk eleman ID, geri kalan sütunlar
                for j in range(1, len(item_data)):
                    self.table.setItem(i, j - 1, QTableWidgetItem(str(item_data[j])))
            else:
                self.table.setItem(i, 0, QTableWidgetItem(str(item_data)))
            self.table.setRowHeight(i, 36)
        self.lbl_count.setText(f"Toplam: {len(items)} kayıt")

    def _filter(self):
        q = self.le_search.text().strip()
        if not q:
            self._populate(self.items)
            return
        filtered = []
        for item_data in self.items:
            if isinstance(item_data, (list, tuple)):
                text = " ".join(str(x) for x in item_data[1:])
            else:
                text = str(item_data)
            if tr_contains(q, text):
                filtered.append(item_data)
        self._populate(filtered)

    def _get_selected_item(self):
        row = self.table.currentRow()
        if row < 0:
            return None
        # Filtreleme sonrasında doğru item'ı bul
        q = self.le_search.text().strip()
        if q:
            filtered = []
            for item_data in self.items:
                if isinstance(item_data, (list, tuple)):
                    text = " ".join(str(x) for x in item_data[1:])
                else:
                    text = str(item_data)
                if tr_contains(q, text):
                    filtered.append(item_data)
            if row < len(filtered):
                return filtered[row]
        else:
            if row < len(self.items):
                return self.items[row]
        return None

    def _select_row(self):
        self._confirm()

    def _confirm(self):
        item = self._get_selected_item()
        if item is None:
            QMessageBox.warning(self, "Uyarı", "Lütfen bir kayıt seçin.")
            return
        if isinstance(item, (list, tuple)):
            self.selected_id = item[0]
        else:
            self.selected_id = item
        self.accept()


class SearchableSelector(QWidget):
    """Aranabilir seçim widget'ı — QLineEdit + Listele butonu"""
    selectionChanged = pyqtSignal(object)

    def __init__(self, items, placeholder="Ara veya seçin...", dialog_title=None,
                 columns=None, parent=None, title=None, **kwargs):
        """
        items: list of (id, display_text) tuples veya (id, col1, col2, ...) tuples
        columns: SearchableListDialog için sütun başlıkları
        """
        super().__init__(parent)
        self._items = items
        self._selected_id = None
        self._dialog_title = title or dialog_title or "Seçim Yapın"
        self._columns = columns
        self._build_ui(placeholder)

    def _build_ui(self, placeholder):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        self.le_search = QLineEdit()
        self.le_search.setPlaceholderText(placeholder)
        self.le_search.setMinimumHeight(32)

        # Completer ile yazarken arama
        display_texts = []
        for item in self._items:
            if isinstance(item, (list, tuple)) and len(item) >= 2:
                display_texts.append(str(item[1]))
            else:
                display_texts.append(str(item))

        self._completer_model = QStringListModel(display_texts)
        completer = QCompleter(self._completer_model)
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        completer.setFilterMode(Qt.MatchFlag.MatchContains)
        completer.setMaxVisibleItems(10)
        completer.activated.connect(self._on_completer_activated)
        self.le_search.setCompleter(completer)

        layout.addWidget(self.le_search)

        btn_browse = btn("📋", "primary", height=32, width=40)
        btn_browse.setToolTip("Tam listeyi aç")
        btn_browse.clicked.connect(self._browse)
        layout.addWidget(btn_browse)

    def _on_completer_activated(self, text):
        """Kullanıcı completer'dan seçim yaptığında"""
        for item in self._items:
            if isinstance(item, (list, tuple)) and len(item) >= 2:
                if str(item[1]) == text:
                    self._selected_id = item[0]
                    self.selectionChanged.emit(item[0])
                    return
            elif str(item) == text:
                self._selected_id = item
                self.selectionChanged.emit(item)
                return

    def _browse(self):
        """Tam liste diyaloğunu aç"""
        dlg = SearchableListDialog(
            self._items,
            title=self._dialog_title,
            columns=self._columns,
            parent=self.window()
        )
        if dlg.exec() == QDialog.DialogCode.Accepted and dlg.selected_id is not None:
            self._selected_id = dlg.selected_id
            # Seçilen item'ın metnini göster
            for item in self._items:
                if isinstance(item, (list, tuple)):
                    if item[0] == dlg.selected_id:
                        self.le_search.setText(str(item[1]))
                        break
            self.selectionChanged.emit(self._selected_id)

    def selectedId(self):
        return self._selected_id

    def setSelectedId(self, item_id):
        self._selected_id = item_id
        for item in self._items:
            if isinstance(item, (list, tuple)):
                if item[0] == item_id:
                    self.le_search.setText(str(item[1]))
                    return
        self.le_search.clear()

    def setText(self, text):
        self.le_search.setText(text)

    def clear(self):
        self._selected_id = None
        self.le_search.clear()

    def updateItems(self, items):
        """Item listesini güncelle"""
        self._items = items
        display_texts = []
        for item in items:
            if isinstance(item, (list, tuple)) and len(item) >= 2:
                display_texts.append(str(item[1]))
            else:
                display_texts.append(str(item))
        self._completer_model.setStringList(display_texts)


# ─── Stok hesaplama ───────────────────────────────────────────────────────────

def get_stock_level(session, product_id, warehouse_id):
    movements = session.query(StockMovement).filter_by(
        product_id=product_id, warehouse_id=warehouse_id
    ).all()
    total = 0.0
    for m in movements:
        if m.movement_type in ("IN", "TRANSFER_IN"):
            total += m.quantity
        elif m.movement_type in ("OUT", "TRANSFER_OUT", "SERVICE_OUT"):
            total -= m.quantity
    return max(0.0, total)


def get_available_serials(session, product_id, warehouse_id):
    """Depodaki kullanılabilir seri numaralarını döndür."""
    return session.query(SerialNumber).filter_by(
        product_id=product_id,
        warehouse_id=warehouse_id,
        status="available"
    ).all()


# ─── Seri No Giriş Diyaloğu (Giriş için) ─────────────────────────────────────

class SerialEntryDialog(QDialog):
    """Stok girişinde seri numarası girmek için."""

    def __init__(self, product_name, quantity, parent=None):
        super().__init__(parent)
        self.quantity = int(quantity)
        self.serial_list = []
        self.setWindowTitle(f"Seri Numaraları — {product_name}")
        self.setMinimumSize(420, 380)
        maximize_dialog(self)
        self._build_ui(product_name)

    def _build_ui(self, product_name):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(12)

        info = QLabel(
            f"<b>{product_name}</b> için <b>{self.quantity}</b> adet seri numarası girilmesi gerekiyor.<br>"
            f"Her satıra bir seri numarası yazın."
        )
        info.setWordWrap(True)
        info.setStyleSheet("color: #4a5568; font-size: 13px;")
        layout.addWidget(info)

        self.te = QTextEdit()
        self.te.setPlaceholderText(
            "Örnek:\nSN-001\nSN-002\nSN-003"
        )
        self.te.setFont(QFont("Courier New", 12))
        layout.addWidget(self.te)

        self.lbl_count = QLabel("")
        self.lbl_count.setStyleSheet("color: #718096; font-size: 12px;")
        layout.addWidget(self.lbl_count)
        self.te.textChanged.connect(self._update_count)

        row = QHBoxLayout()
        btn_cancel = btn("İptal", "secondary")
        btn_ok = btn("Onayla", "success")
        btn_cancel.clicked.connect(self.reject)
        btn_ok.clicked.connect(self._confirm)
        row.addStretch()
        row.addWidget(btn_cancel)
        row.addWidget(btn_ok)
        layout.addLayout(row)

    def _update_count(self):
        lines = [l.strip() for l in self.te.toPlainText().splitlines() if l.strip()]
        n = len(lines)
        color = "#38a169" if n == self.quantity else "#e53e3e"
        self.lbl_count.setText(
            f'<span style="color:{color}">Girilen: <b>{n}</b> / Gereken: <b>{self.quantity}</b></span>'
        )

    def _confirm(self):
        lines = [l.strip() for l in self.te.toPlainText().splitlines() if l.strip()]
        if len(lines) != self.quantity:
            QMessageBox.warning(
                self, "Uyarı",
                f"Tam olarak {self.quantity} seri numarası girilmelidir.\n"
                f"Şu an {len(lines)} satır var."
            )
            return
        # Tekrar kontrolü
        if len(set(lines)) != len(lines):
            QMessageBox.warning(self, "Uyarı", "Aynı seri numarasını birden fazla kez girdiniz.")
            return
        self.serial_list = lines
        self.accept()


# ─── Seri No Seçim Diyaloğu (Çıkış için) ─────────────────────────────────────

class SerialSelectDialog(QDialog):
    """Stok çıkışında mevcut seri numaralarından seçim yapmak için."""

    def __init__(self, product_name, serials, quantity, parent=None):
        super().__init__(parent)
        self.quantity = int(quantity)
        self.selected_serials = []
        self.setWindowTitle(f"Seri No Seç — {product_name}")
        self.setMinimumSize(380, 400)
        maximize_dialog(self)
        self._build_ui(product_name, serials)

    def _build_ui(self, product_name, serials):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(12)

        info = QLabel(
            f"<b>{self.quantity}</b> adet seri numarası seçin:"
        )
        info.setStyleSheet("color: #4a5568; font-size: 13px;")
        layout.addWidget(info)

        self.list_widget = QListWidget()
        self.list_widget.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)
        for sn in serials:
            item = QListWidgetItem(sn.serial_no)
            self.list_widget.addItem(item)
        self.list_widget.itemSelectionChanged.connect(self._update_count)
        layout.addWidget(self.list_widget)

        self.lbl_count = QLabel("")
        self.lbl_count.setStyleSheet("color: #718096; font-size: 12px;")
        layout.addWidget(self.lbl_count)
        self._update_count()

        row = QHBoxLayout()
        btn_cancel = btn("İptal", "secondary")
        btn_ok = btn("Onayla", "success")
        btn_cancel.clicked.connect(self.reject)
        btn_ok.clicked.connect(self._confirm)
        row.addStretch()
        row.addWidget(btn_cancel)
        row.addWidget(btn_ok)
        layout.addLayout(row)

    def _update_count(self):
        n = len(self.list_widget.selectedItems())
        color = "#38a169" if n == self.quantity else "#e53e3e"
        self.lbl_count.setText(
            f'<span style="color:{color}">Seçilen: <b>{n}</b> / Gereken: <b>{self.quantity}</b></span>'
        )

    def _confirm(self):
        selected = self.list_widget.selectedItems()
        if len(selected) != self.quantity:
            QMessageBox.warning(
                self, "Uyarı",
                f"Tam olarak {self.quantity} seri numarası seçilmelidir.\n"
                f"Şu an {len(selected)} seçili."
            )
            return
        self.selected_serials = [item.text() for item in selected]
        self.accept()


# ─── Ürün Stok Detayı (Çift Tıklama) ─────────────────────────────────────────

class ProductStockDetailDialog(QDialog):
    def __init__(self, session, product, parent=None):
        super().__init__(parent)
        self.session = session
        self.product = product
        self.setWindowTitle(f"Stok Detayı — {product.name}")
        self.setMinimumSize(600, 550)
        maximize_dialog(self)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; }")

        content = QWidget()
        cl = QVBoxLayout(content)
        cl.setSpacing(12)

        # Product Info
        info_group = QGroupBox("📦 Ürün Bilgileri")
        info_group.setStyleSheet("QGroupBox { font-weight: bold; }")
        ig = QFormLayout(info_group)
        ig.addRow("Ad:", QLabel(f"<b>{self.product.name}</b>"))
        ig.addRow("Kod:", QLabel(self.product.product_code or "—"))
        ig.addRow("Kategori:", QLabel(self.product.category or "—"))
        desc = QLabel(self.product.description or "—")
        desc.setWordWrap(True)
        ig.addRow("Açıklama:", desc)
        cl.addWidget(info_group)

        # Stock levels
        stock_group = QGroupBox("📊 Depo Stok Durumları")
        stock_group.setStyleSheet("QGroupBox { font-weight: bold; }")
        sg = QVBoxLayout(stock_group)
        warehouses = self.session.query(Warehouse).filter_by(is_active=True).all()

        st_table = QTableWidget()
        st_table.setColumnCount(2)
        st_table.setHorizontalHeaderLabels(["Depo", "Miktar"])
        st_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        st_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        st_table.verticalHeader().setVisible(False)
        st_table.setAlternatingRowColors(True)

        row = 0
        total_stock = 0
        for w in warehouses:
            lvl = get_stock_level(self.session, self.product.id, w.id)
            if lvl > 0:
                st_table.insertRow(row)
                st_table.setItem(row, 0, QTableWidgetItem(w.name))
                qty_item = QTableWidgetItem(f"{lvl:g} {self.product.unit}")
                qty_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                st_table.setItem(row, 1, qty_item)
                total_stock += lvl
                row += 1
        sg.addWidget(st_table)

        tot_lbl = QLabel(f"Toplam Stok: <b>{total_stock:g} {self.product.unit}</b>")
        tot_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
        tot_lbl.setStyleSheet("color: #2b6cb0; font-size: 13px;")
        sg.addWidget(tot_lbl)

        cl.addWidget(stock_group)

        # Serial numbers
        if self.product.serial_tracking:
            ser_group = QGroupBox("🔢 Seri Numaraları (Boşta)")
            ser_group.setStyleSheet("QGroupBox { font-weight: bold; }")
            srg = QVBoxLayout(ser_group)

            sr_table = QTableWidget()
            sr_table.setColumnCount(2)
            sr_table.setHorizontalHeaderLabels(["Seri No", "Depo"])
            sr_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
            sr_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
            sr_table.verticalHeader().setVisible(False)
            sr_table.setAlternatingRowColors(True)

            serials = self.session.query(SerialNumber).filter_by(
                product_id=self.product.id, status="available"
            ).all()

            sr_table.setRowCount(len(serials))
            for i, sn in enumerate(serials):
                sr_table.setItem(i, 0, QTableWidgetItem(sn.serial_no))
                try:
                    w_name = sn.warehouse.name if sn.warehouse else "Bilinmiyor"
                except Exception:
                    if sn.warehouse_id:
                        wh = self.session.get(Warehouse, sn.warehouse_id)
                        w_name = wh.name if wh else "Bilinmiyor"
                    else:
                        w_name = "Bilinmiyor"
                sr_table.setItem(i, 1, QTableWidgetItem(w_name))

            srg.addWidget(sr_table)
            cl.addWidget(ser_group)

        scroll.setWidget(content)
        layout.addWidget(scroll)

        btn_close = btn("Kapat", "secondary")
        btn_close.clicked.connect(self.accept)
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_layout.addWidget(btn_close)
        layout.addLayout(btn_layout)


# ─── Stok Girişi ──────────────────────────────────────────────────────────────

class StockInDialog(QDialog):
    def __init__(self, session, user, product=None, parent=None):
        super().__init__(parent)
        self.session = session
        self.user = user
        self._serial_list = []
        self.setWindowTitle("Stok Girişi")
        self.setMinimumWidth(450)
        maximize_dialog(self)
        self._build_ui(product)

    def _build_ui(self, preselect_product=None):
        layout = QFormLayout(self)
        layout.setContentsMargins(25, 20, 25, 20)
        layout.setSpacing(13)

        title = QLabel("📦 Stok Girişi")
        title.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        title.setStyleSheet("color: #38a169;")
        layout.addRow(title)

        # Ürün seçimi — aramalı
        products = self.session.query(Product).filter_by(is_active=True).all()
        product_items = []
        for p in products:
            label = f"{p.product_code} — {p.name}"
            if p.serial_tracking:
                label += "  🔢"
            product_items.append((p.id, label))

        self.sel_product = SearchableSelector(
            product_items, placeholder="Ürün ara veya listele...",
            dialog_title="Ürün Seçin", columns=["Ürün"]
        )
        self.sel_product.selectionChanged.connect(self._on_product_changed)
        if preselect_product:
            self.sel_product.setSelectedId(preselect_product.id)

        # Depo seçimi — aramalı
        warehouses = self.session.query(Warehouse).filter_by(is_active=True).all()
        wh_items = [(w.id, w.name) for w in warehouses]
        self.sel_warehouse = SearchableSelector(
            wh_items, placeholder="Depo ara veya listele...",
            dialog_title="Depo Seçin", columns=["Depo"]
        )

        self.spin_qty = QDoubleSpinBox()
        self.spin_qty.setMinimum(1)
        self.spin_qty.setMaximum(999999)
        self.spin_qty.setValue(1)
        self.spin_qty.setDecimals(0)

        self.le_reason = QLineEdit()
        self.le_reason.setPlaceholderText("Giriş nedeni (opsiyonel)")

        # Seri no bölümü
        self.serial_group = QGroupBox("🔢 Seri Numaraları")
        sg = QVBoxLayout(self.serial_group)
        self.lbl_serials = QLabel("Seri no girilmedi.")
        self.lbl_serials.setStyleSheet("color: #718096; font-size: 12px;")
        self.btn_enter_serials = btn("Seri Numarası Gir", "primary", height=30)
        self.btn_enter_serials.clicked.connect(self._enter_serials)
        sg.addWidget(self.lbl_serials)
        sg.addWidget(self.btn_enter_serials)
        self.serial_group.hide()

        self.spin_qty.valueChanged.connect(self._on_qty_changed)

        layout.addRow("Ürün *:", self.sel_product)
        layout.addRow("Depo *:", self.sel_warehouse)
        layout.addRow("Miktar *:", self.spin_qty)
        layout.addRow("Açıklama:", self.le_reason)
        layout.addRow(self.serial_group)

        row = QHBoxLayout()
        btn_cancel = btn("İptal", "secondary")
        btn_ok = btn("💾 Kaydet", "success")
        btn_cancel.clicked.connect(self.reject)
        btn_ok.clicked.connect(self._save)
        row.addStretch()
        row.addWidget(btn_cancel)
        row.addWidget(btn_ok)
        layout.addRow(row)

    def _current_product(self):
        pid = self.sel_product.selectedId()
        if not pid:
            return None
        return self.session.get(Product, pid)

    def _on_product_changed(self, pid):
        self._serial_list = []
        p = self.session.get(Product, pid) if pid else None
        if p and p.serial_tracking:
            self.serial_group.show()
            self._update_serial_label()
        else:
            self.serial_group.hide()

    def _on_qty_changed(self):
        self._serial_list = []
        if self.serial_group.isVisible():
            self._update_serial_label()

    def _update_serial_label(self):
        n = len(self._serial_list)
        needed = int(self.spin_qty.value())
        if n == 0:
            self.lbl_serials.setText(f"⚠️  {needed} seri numarası girilmesi gerekiyor.")
            self.lbl_serials.setStyleSheet("color: #e53e3e; font-size: 12px;")
        elif n == needed:
            self.lbl_serials.setText(f"✓  {n} seri numarası girildi: {', '.join(self._serial_list[:3])}{'...' if n > 3 else ''}")
            self.lbl_serials.setStyleSheet("color: #38a169; font-size: 12px;")
        else:
            self.lbl_serials.setText(f"⚠️  {n}/{needed} seri numarası girildi.")
            self.lbl_serials.setStyleSheet("color: #d69e2e; font-size: 12px;")

    def _enter_serials(self):
        p = self._current_product()
        if not p:
            return
        qty = int(self.spin_qty.value())
        dlg = SerialEntryDialog(p.name, qty, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._serial_list = dlg.serial_list
            self._update_serial_label()

    def _save(self):
        pid = self.sel_product.selectedId()
        wid = self.sel_warehouse.selectedId()
        qty = int(self.spin_qty.value())
        if not pid or not wid:
            QMessageBox.warning(self, "Uyarı", "Ürün ve depo seçimi zorunludur.")
            return

        p = self.session.get(Product, pid)
        if p.serial_tracking and len(self._serial_list) != qty:
            QMessageBox.warning(
                self, "Uyarı",
                f"Seri takipli ürün — {qty} adet için seri numarası girilmesi zorunludur."
            )
            return

        try:
            mv = StockMovement(
                product_id=pid,
                warehouse_id=wid,
                movement_type="IN",
                quantity=qty,
                serial_numbers_json=self._serial_list if self._serial_list else None,
                reason=self.le_reason.text().strip() or "Manuel giriş",
                reference_type="MANUAL",
                user_id=self.user.id,
            )
            self.session.add(mv)
            self.session.flush()

            # Seri numaralarını kaydet
            for sn in self._serial_list:
                existing = self.session.query(SerialNumber).filter_by(
                    product_id=pid, serial_no=sn
                ).first()
                if existing:
                    existing.warehouse_id = wid
                    existing.status = "available"
                else:
                    self.session.add(SerialNumber(
                        product_id=pid,
                        serial_no=sn,
                        status="available",
                        warehouse_id=wid,
                    ))

            self.session.commit()
            self.accept()
        except Exception as e:
            self.session.rollback()
            QMessageBox.critical(self, "Hata", str(e))


# ─── Stok Çıkışı ──────────────────────────────────────────────────────────────

class StockOutDialog(QDialog):
    def __init__(self, session, user, parent=None):
        super().__init__(parent)
        self.session = session
        self.user = user
        self._selected_serials = []
        self.setWindowTitle("Stok Çıkışı")
        self.setMinimumWidth(450)
        maximize_dialog(self)
        self._build_ui()

    def _build_ui(self):
        layout = QFormLayout(self)
        layout.setContentsMargins(25, 20, 25, 20)
        layout.setSpacing(13)

        title = QLabel("📤 Stok Çıkışı")
        title.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        title.setStyleSheet("color: #e53e3e;")
        layout.addRow(title)

        # Ürün seçimi — aramalı
        products = self.session.query(Product).filter_by(is_active=True).all()
        product_items = []
        for p in products:
            label = f"{p.product_code} — {p.name}"
            if p.serial_tracking:
                label += "  🔢"
            product_items.append((p.id, label))

        self.sel_product = SearchableSelector(
            product_items, placeholder="Ürün ara veya listele...",
            dialog_title="Ürün Seçin", columns=["Ürün"]
        )
        self.sel_product.selectionChanged.connect(self._update_info)

        # Depo seçimi — aramalı
        warehouses = self.session.query(Warehouse).filter_by(is_active=True).all()
        wh_items = [(w.id, w.name) for w in warehouses]
        self.sel_warehouse = SearchableSelector(
            wh_items, placeholder="Depo ara veya listele...",
            dialog_title="Depo Seçin", columns=["Depo"]
        )
        self.sel_warehouse.selectionChanged.connect(self._update_info)

        self.spin_qty = QDoubleSpinBox()
        self.spin_qty.setMinimum(1)
        self.spin_qty.setMaximum(999999)
        self.spin_qty.setValue(1)
        self.spin_qty.setDecimals(0)

        self.le_reason = QLineEdit()
        self.le_reason.setPlaceholderText("Çıkış nedeni")

        self.lbl_stock = QLabel("")
        self.lbl_stock.setStyleSheet("color: #3182ce; font-size: 12px;")

        # Seri no bölümü
        self.serial_group = QGroupBox("🔢 Seri Numaraları")
        sg = QVBoxLayout(self.serial_group)
        self.lbl_serials_out = QLabel("Seri no seçilmedi.")
        self.lbl_serials_out.setStyleSheet("color: #718096; font-size: 12px;")
        self.btn_select_serials = btn("Seri No Seç", "primary", height=30)
        self.btn_select_serials.clicked.connect(self._select_serials)
        sg.addWidget(self.lbl_serials_out)
        sg.addWidget(self.btn_select_serials)
        self.serial_group.hide()

        self.spin_qty.valueChanged.connect(self._on_qty_changed)

        layout.addRow("Ürün *:", self.sel_product)
        layout.addRow("Depo *:", self.sel_warehouse)
        layout.addRow("Miktar *:", self.spin_qty)
        layout.addRow("Açıklama:", self.le_reason)
        layout.addRow(self.lbl_stock)
        layout.addRow(self.serial_group)

        row = QHBoxLayout()
        btn_cancel = btn("İptal", "secondary")
        btn_ok = btn("💾 Kaydet", "danger")
        btn_cancel.clicked.connect(self.reject)
        btn_ok.clicked.connect(self._save)
        row.addStretch()
        row.addWidget(btn_cancel)
        row.addWidget(btn_ok)
        layout.addRow(row)

    def _update_info(self, _=None):
        self._selected_serials = []
        pid = self.sel_product.selectedId()
        wid = self.sel_warehouse.selectedId()
        if pid and wid:
            lvl = get_stock_level(self.session, pid, wid)
            p = self.session.get(Product, pid)
            self.lbl_stock.setText(f"Mevcut stok: <b>{lvl:g}</b> {p.unit}")
            if p.serial_tracking:
                self.serial_group.show()
                self._update_serial_label_out()
            else:
                self.serial_group.hide()
        else:
            self.lbl_stock.setText("")
            self.serial_group.hide()

    def _on_qty_changed(self):
        self._selected_serials = []
        if self.serial_group.isVisible():
            self._update_serial_label_out()

    def _update_serial_label_out(self):
        n = len(self._selected_serials)
        needed = int(self.spin_qty.value())
        if n == 0:
            self.lbl_serials_out.setText(f"⚠️  {needed} seri numarası seçilmesi gerekiyor.")
            self.lbl_serials_out.setStyleSheet("color: #e53e3e; font-size: 12px;")
        elif n == needed:
            txt = ', '.join(self._selected_serials[:3]) + ('...' if n > 3 else '')
            self.lbl_serials_out.setText(f"✓  Seçilen: {txt}")
            self.lbl_serials_out.setStyleSheet("color: #38a169; font-size: 12px;")
        else:
            self.lbl_serials_out.setText(f"⚠️  {n}/{needed} seçildi.")
            self.lbl_serials_out.setStyleSheet("color: #d69e2e; font-size: 12px;")

    def _select_serials(self):
        pid = self.sel_product.selectedId()
        wid = self.sel_warehouse.selectedId()
        if not pid or not wid:
            QMessageBox.warning(self, "Uyarı", "Önce ürün ve depo seçin.")
            return
        p = self.session.get(Product, pid)
        serials = get_available_serials(self.session, pid, wid)
        if not serials:
            QMessageBox.warning(self, "Uyarı", "Bu depoda kayıtlı seri numarası bulunamadı.")
            return
        qty = int(self.spin_qty.value())
        dlg = SerialSelectDialog(p.name, serials, qty, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._selected_serials = dlg.selected_serials
            self._update_serial_label_out()

    def _save(self):
        pid = self.sel_product.selectedId()
        wid = self.sel_warehouse.selectedId()
        qty = int(self.spin_qty.value())
        if not pid or not wid:
            QMessageBox.warning(self, "Uyarı", "Ürün ve depo seçimi zorunludur.")
            return

        p = self.session.get(Product, pid)
        if p.serial_tracking and len(self._selected_serials) != qty:
            QMessageBox.warning(
                self, "Uyarı",
                f"Seri takipli ürün — {qty} adet için seri numarası seçilmesi zorunludur."
            )
            return

        current = get_stock_level(self.session, pid, wid)
        if qty > current:
            QMessageBox.warning(self, "Yetersiz Stok",
                                f"Mevcut stok: {current:g}\nTalep edilen: {qty:g}")
            return

        try:
            mv = StockMovement(
                product_id=pid,
                warehouse_id=wid,
                movement_type="OUT",
                quantity=qty,
                serial_numbers_json=self._selected_serials if self._selected_serials else None,
                reason=self.le_reason.text().strip() or "Manuel çıkış",
                reference_type="MANUAL",
                user_id=self.user.id,
            )
            self.session.add(mv)

            # Seri no durumlarını güncelle
            for sn_str in self._selected_serials:
                sn = self.session.query(SerialNumber).filter_by(
                    product_id=pid, serial_no=sn_str, warehouse_id=wid
                ).first()
                if sn:
                    sn.status = "used"

            self.session.commit()
            self.accept()
        except Exception as e:
            self.session.rollback()
            QMessageBox.critical(self, "Hata", str(e))


# ─── Depo Transferi ───────────────────────────────────────────────────────────

class TransferDialog(QDialog):
    def __init__(self, session, user, parent=None):
        super().__init__(parent)
        self.session = session
        self.user = user
        self._selected_serials = []
        self.setWindowTitle("Depo Transferi")
        self.setMinimumWidth(460)
        maximize_dialog(self)
        self._build_ui()

    def _build_ui(self):
        layout = QFormLayout(self)
        layout.setContentsMargins(25, 20, 25, 20)
        layout.setSpacing(13)

        title = QLabel("🔄 Depo Transferi")
        title.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        title.setStyleSheet("color: #d69e2e;")
        layout.addRow(title)

        # Ürün seçimi — aramalı
        products = self.session.query(Product).filter_by(is_active=True).all()
        product_items = []
        for p in products:
            label = f"{p.product_code} — {p.name}"
            if p.serial_tracking:
                label += "  🔢"
            product_items.append((p.id, label))

        self.sel_product = SearchableSelector(
            product_items, placeholder="Ürün ara veya listele...",
            dialog_title="Ürün Seçin", columns=["Ürün"]
        )
        self.sel_product.selectionChanged.connect(self._update_info)

        # Depo seçimleri — aramalı
        warehouses = self.session.query(Warehouse).filter_by(is_active=True).all()
        wh_items = [(w.id, w.name) for w in warehouses]

        self.sel_src = SearchableSelector(
            wh_items, placeholder="Kaynak depo ara...",
            dialog_title="Kaynak Depo Seçin", columns=["Depo"]
        )
        self.sel_src.selectionChanged.connect(self._update_info)

        self.sel_dst = SearchableSelector(
            wh_items, placeholder="Hedef depo ara...",
            dialog_title="Hedef Depo Seçin", columns=["Depo"]
        )

        self.spin_qty = QDoubleSpinBox()
        self.spin_qty.setMinimum(1)
        self.spin_qty.setMaximum(999999)
        self.spin_qty.setValue(1)
        self.spin_qty.setDecimals(0)

        self.lbl_stock = QLabel("")
        self.lbl_stock.setStyleSheet("color: #3182ce; font-size: 12px;")

        self.serial_group = QGroupBox("🔢 Seri Numaraları")
        sg = QVBoxLayout(self.serial_group)
        self.lbl_serials = QLabel("Seri no seçilmedi.")
        self.lbl_serials.setStyleSheet("color: #718096; font-size: 12px;")
        self.btn_sel = btn("Seri No Seç", "primary", height=30)
        self.btn_sel.clicked.connect(self._select_serials)
        sg.addWidget(self.lbl_serials)
        sg.addWidget(self.btn_sel)
        self.serial_group.hide()

        self.spin_qty.valueChanged.connect(self._on_qty_changed)

        layout.addRow("Ürün *:", self.sel_product)
        layout.addRow("Kaynak Depo *:", self.sel_src)
        layout.addRow("Hedef Depo *:", self.sel_dst)
        layout.addRow("Miktar *:", self.spin_qty)
        layout.addRow(self.lbl_stock)
        layout.addRow(self.serial_group)

        row = QHBoxLayout()
        btn_cancel = btn("İptal", "secondary")
        btn_ok = btn("🔄 Transfer Et", "warning")
        btn_cancel.clicked.connect(self.reject)
        btn_ok.clicked.connect(self._save)
        row.addStretch()
        row.addWidget(btn_cancel)
        row.addWidget(btn_ok)
        layout.addRow(row)

    def _update_info(self, _=None):
        self._selected_serials = []
        pid = self.sel_product.selectedId()
        wid = self.sel_src.selectedId()
        if pid and wid:
            lvl = get_stock_level(self.session, pid, wid)
            p = self.session.get(Product, pid)
            self.lbl_stock.setText(f"Kaynak depodaki stok: <b>{lvl:g}</b> {p.unit}")
            if p.serial_tracking:
                self.serial_group.show()
            else:
                self.serial_group.hide()
        else:
            self.lbl_stock.setText("")
            self.serial_group.hide()

    def _on_qty_changed(self):
        self._selected_serials = []
        if self.serial_group.isVisible():
            self.lbl_serials.setText("Seri no seçilmedi.")

    def _select_serials(self):
        pid = self.sel_product.selectedId()
        wid = self.sel_src.selectedId()
        if not pid or not wid:
            return
        p = self.session.get(Product, pid)
        serials = get_available_serials(self.session, pid, wid)
        qty = int(self.spin_qty.value())
        dlg = SerialSelectDialog(p.name, serials, qty, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._selected_serials = dlg.selected_serials
            n = len(self._selected_serials)
            self.lbl_serials.setText(f"✓ {n} seri numarası seçildi.")
            self.lbl_serials.setStyleSheet("color: #38a169; font-size: 12px;")

    def _save(self):
        pid = self.sel_product.selectedId()
        src = self.sel_src.selectedId()
        dst = self.sel_dst.selectedId()
        qty = int(self.spin_qty.value())
        if not pid or not src or not dst:
            QMessageBox.warning(self, "Uyarı", "Tüm alanlar zorunludur.")
            return
        if src == dst:
            QMessageBox.warning(self, "Uyarı", "Kaynak ve hedef depo aynı olamaz.")
            return

        p = self.session.get(Product, pid)
        if p.serial_tracking and len(self._selected_serials) != qty:
            QMessageBox.warning(self, "Uyarı", f"Seri takipli ürün — {qty} adet seri no seçilmesi gerekiyor.")
            return

        current = get_stock_level(self.session, pid, src)
        if qty > current:
            QMessageBox.warning(self, "Yetersiz Stok", f"Kaynak stok: {current:g} / Talep: {qty:g}")
            return

        try:
            out_mv = StockMovement(
                product_id=pid, warehouse_id=src,
                movement_type="TRANSFER_OUT", quantity=qty,
                serial_numbers_json=self._selected_serials or None,
                reason="Depo transferi", reference_type="TRANSFER",
                user_id=self.user.id,
            )
            in_mv = StockMovement(
                product_id=pid, warehouse_id=dst,
                movement_type="TRANSFER_IN", quantity=qty,
                serial_numbers_json=self._selected_serials or None,
                reason="Depo transferi", reference_type="TRANSFER",
                user_id=self.user.id,
            )
            self.session.add_all([out_mv, in_mv])
            self.session.flush()
            out_mv.reference_id = in_mv.id
            in_mv.reference_id = out_mv.id

            # Seri no depo güncelle
            for sn_str in self._selected_serials:
                sn = self.session.query(SerialNumber).filter_by(
                    product_id=pid, serial_no=sn_str, warehouse_id=src
                ).first()
                if sn:
                    sn.warehouse_id = dst

            self.session.commit()
            self.accept()
        except Exception as e:
            self.session.rollback()
            QMessageBox.critical(self, "Hata", str(e))


# ─── Stok Ana Sayfası ─────────────────────────────────────────────────────────

class StockPage(QWidget):
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

        # Top bar
        top = QHBoxLayout()
        title = QLabel("Stok Yönetimi")
        title.setFont(QFont("Segoe UI", 15, QFont.Weight.Bold))
        top.addWidget(title)
        top.addStretch()

        self.le_search = QLineEdit()
        self.le_search.setPlaceholderText("🔍 Ürün veya depo ara...")
        self.le_search.setFixedWidth(220)
        self.le_search.setMinimumHeight(34)
        self.le_search.textChanged.connect(self._filter)
        top.addWidget(self.le_search)

        if self.user.role.can_create:
            self.btn_in = btn("📦 Stok Girişi", "success")
            self.btn_in.clicked.connect(self._stock_in)
            top.addWidget(self.btn_in)

            self.btn_out = btn("📤 Stok Çıkışı", "danger")
            self.btn_out.clicked.connect(self._stock_out)
            top.addWidget(self.btn_out)

            self.btn_transfer = btn("🔄 Transfer", "warning")
            self.btn_transfer.clicked.connect(self._transfer)
            top.addWidget(self.btn_transfer)

        layout.addLayout(top)

        self.stats_label = QLabel("")
        self.stats_label.setStyleSheet("color: #718096; font-size: 12px;")
        layout.addWidget(self.stats_label)

        tabs = QTabWidget()

        # Stok Özeti
        self.stock_table = QTableWidget()
        self.stock_table.setColumnCount(6)
        self.stock_table.setHorizontalHeaderLabels(["Ürün Kodu", "Ürün Adı", "Depo", "Miktar", "Birim", "Seri Takip"])
        hh = self.stock_table.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        hh.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        hh.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        self.stock_table.setAlternatingRowColors(True)
        self.stock_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.stock_table.verticalHeader().setVisible(False)
        self.stock_table.doubleClicked.connect(self._show_serials)
        tabs.addTab(self.stock_table, "📊 Stok Durumu")

        # Hareketler
        self.mv_table = QTableWidget()
        self.mv_table.setColumnCount(7)
        self.mv_table.setHorizontalHeaderLabels(["Tarih", "Ürün", "Depo", "Tür", "Miktar", "Seri Nolar", "Kullanıcı"])
        hh_mv = self.mv_table.horizontalHeader()
        hh_mv.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        hh_mv.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        hh_mv.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        hh_mv.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        hh_mv.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        hh_mv.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        hh_mv.setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)
        hh_mv.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)
        self.mv_table.setAlternatingRowColors(True)
        self.mv_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.mv_table.verticalHeader().setVisible(False)
        tabs.addTab(self.mv_table, "📋 Stok Hareketleri")

        layout.addWidget(tabs)

        hint = QLabel("💡 Stok satırına çift tıklayarak seri numaralarını görüntüleyebilirsiniz.")
        hint.setStyleSheet("color: #a0aec0; font-size: 11px;")
        layout.addWidget(hint)

    def refresh(self):
        self._load_stock_summary()
        self._load_movements()

    def _load_stock_summary(self):
        products = self.session.query(Product).filter_by(is_active=True).all()
        warehouses = self.session.query(Warehouse).filter_by(is_active=True).all()
        rows = []
        for p in products:
            for w in warehouses:
                lvl = get_stock_level(self.session, p.id, w.id)
                if lvl > 0:
                    rows.append((p, w, lvl))
        self._stock_rows = rows
        self.stats_label.setText(f"Stok kaydı: {len(rows)} satır")
        self._populate_stock(rows)

    def _populate_stock(self, rows):
        self.stock_table.setRowCount(len(rows))
        for i, (p, w, lvl) in enumerate(rows):
            self.stock_table.setItem(i, 0, QTableWidgetItem(p.product_code))
            self.stock_table.setItem(i, 1, QTableWidgetItem(p.name))
            self.stock_table.setItem(i, 2, QTableWidgetItem(w.name))

            qty_item = QTableWidgetItem(f"{lvl:g}")
            qty_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            if lvl <= 5:
                qty_item.setForeground(QColor("#e53e3e"))
                qty_item.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
            self.stock_table.setItem(i, 3, qty_item)
            self.stock_table.setItem(i, 4, QTableWidgetItem(p.unit))

            serial_item = QTableWidgetItem("🔢 Evet" if p.serial_tracking else "—")
            serial_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            serial_item.setForeground(QColor("#3182ce") if p.serial_tracking else QColor("#a0aec0"))
            self.stock_table.setItem(i, 5, serial_item)

    def _show_serials(self, index):
        if not hasattr(self, '_stock_rows'):
            return
        row = index.row()
        if row >= len(self._stock_rows):
            return
        p, w, lvl = self._stock_rows[row]
        dlg = ProductStockDetailDialog(self.session, p, parent=self)
        dlg.exec()

    def _load_movements(self):
        mvs = (self.session.query(StockMovement)
               .order_by(StockMovement.created_at.desc())
               .limit(200).all())
        self.mv_table.setRowCount(len(mvs))

        type_labels = {
            "IN":           ("📦 Giriş",         "#38a169"),
            "OUT":          ("📤 Çıkış",          "#e53e3e"),
            "TRANSFER_IN":  ("🔄 Transfer Giriş", "#3182ce"),
            "TRANSFER_OUT": ("🔄 Transfer Çıkış", "#d69e2e"),

        }

        for i, m in enumerate(mvs):
            date_str = m.created_at.strftime("%d.%m.%Y %H:%M") if m.created_at else ""
            self.mv_table.setItem(i, 0, QTableWidgetItem(date_str))
            self.mv_table.setItem(i, 1, QTableWidgetItem(m.product.name if m.product else ""))
            self.mv_table.setItem(i, 2, QTableWidgetItem(m.warehouse.name if m.warehouse else ""))

            lbl, color = type_labels.get(m.movement_type, (m.movement_type, "#4a5568"))
            type_item = QTableWidgetItem(lbl)
            type_item.setForeground(QColor(color))
            self.mv_table.setItem(i, 3, type_item)

            qty_item = QTableWidgetItem(f"{m.quantity:g}")
            qty_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.mv_table.setItem(i, 4, qty_item)

            serials = m.serial_numbers_json
            serial_str = ", ".join(serials[:3]) + ("..." if serials and len(serials) > 3 else "") if serials else "—"
            self.mv_table.setItem(i, 5, QTableWidgetItem(serial_str))

            user_name = m.user.full_name if m.user else ""
            self.mv_table.setItem(i, 6, QTableWidgetItem(user_name))

    def _filter(self):
        q = self.le_search.text().strip()
        if not q or not hasattr(self, '_stock_rows'):
            self._populate_stock(self._stock_rows if hasattr(self, '_stock_rows') else [])
            return
        filtered = [(p, w, lvl) for p, w, lvl in self._stock_rows
                    if tr_contains(q, p.name) or tr_contains(q, w.name) or tr_contains(q, p.product_code)]
        self._populate_stock(filtered)

    def _stock_in(self):
        dlg = StockInDialog(self.session, self.user, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.refresh()

    def _stock_out(self):
        dlg = StockOutDialog(self.session, self.user, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.refresh()

    def _transfer(self):
        dlg = TransferDialog(self.session, self.user, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.refresh()
