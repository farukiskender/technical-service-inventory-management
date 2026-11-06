"""
Kişiler Modülü — Müşteri ve İlgili Kişi Yönetimi
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QDialog, QFormLayout,
    QLineEdit, QCheckBox, QTextEdit, QHeaderView,
    QMessageBox, QFrame
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QColor

from shared.schema import Person
from shared.utils import tr_contains
from main_app.ui.stock_page import btn, maximize_dialog


class PersonDialog(QDialog):
    def __init__(self, session, user, person=None, parent=None):
        super().__init__(parent)
        self.session = session
        self.user = user
        self.person = person
        self.setWindowTitle("Kişi Ekle" if not person else "Kişi Düzenle")
        self.setMinimumWidth(500)
        maximize_dialog(self)
        self._build_ui()
        if person:
            self._load()

    def _build_ui(self):
        layout = QFormLayout(self)
        layout.setContentsMargins(25, 25, 25, 20)
        layout.setSpacing(13)

        title = QLabel("👤 Kişi Bilgileri")
        title.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        title.setStyleSheet("color: #2b6cb0; margin-bottom: 5px;")
        layout.addRow(title)

        self.le_name = QLineEdit()
        self.le_name.setPlaceholderText("Ad Soyad")
        layout.addRow("Ad Soyad *:", self.le_name)

        self.le_tc = QLineEdit()
        self.le_tc.setPlaceholderText("11 haneli TC Kimlik No")
        self.le_tc.setMaxLength(11)
        layout.addRow("TC Kimlik No:", self.le_tc)

        self.le_title = QLineEdit()
        self.le_title.setPlaceholderText("Ünvan (örn: Müdür, Teknisyen, Şirket Yetkilisi)")
        layout.addRow("Ünvan:", self.le_title)

        self.le_phone = QLineEdit()
        self.le_phone.setPlaceholderText("05XX XXX XX XX")
        layout.addRow("Telefon *:", self.le_phone)

        self.le_email = QLineEdit()
        self.le_email.setPlaceholderText("ornek@email.com")
        layout.addRow("E-Posta:", self.le_email)

        self.le_address = QTextEdit()
        self.le_address.setMaximumHeight(70)
        self.le_address.setPlaceholderText("Adres bilgisi")
        layout.addRow("Adres:", self.le_address)

        self.te_notes = QTextEdit()
        self.te_notes.setMaximumHeight(70)
        self.te_notes.setPlaceholderText("Ek notlar...")
        layout.addRow("Notlar:", self.te_notes)

        self.chk_active = QCheckBox("Aktif")
        self.chk_active.setChecked(True)
        layout.addRow("", self.chk_active)

        # Butonlar
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
        p = self.person
        self.le_name.setText(p.name or "")
        self.le_tc.setText(p.tc_no or "")
        self.le_title.setText(p.title or "")
        self.le_phone.setText(p.phone or "")
        self.le_email.setText(p.email or "")
        self.le_address.setPlainText(p.address or "")
        self.te_notes.setPlainText(p.notes or "")
        self.chk_active.setChecked(p.is_active if p.is_active is not None else True)

    def _save(self):
        name = self.le_name.text().strip()
        phone = self.le_phone.text().strip()
        tc = self.le_tc.text().strip()

        if not name:
            QMessageBox.warning(self, "Uyarı", "Ad soyad zorunludur.")
            self.le_name.setFocus()
            return

        if not phone:
            QMessageBox.warning(self, "Uyarı", "Telefon numarası zorunludur.")
            self.le_phone.setFocus()
            return

        if tc:
            if not tc.isdigit():
                QMessageBox.warning(self, "Uyarı", "TC Kimlik No sadece rakamlardan oluşmalıdır.")
                self.le_tc.setFocus()
                return
            if len(tc) != 11:
                QMessageBox.warning(self, "Uyarı", "TC Kimlik No 11 haneli olmalıdır.")
                self.le_tc.setFocus()
                return

        # Telefon unique kontrolü
        query = self.session.query(Person).filter(Person.phone == phone)
        if self.person:
            query = query.filter(Person.id != self.person.id)
        existing = query.first()
        if existing:
            QMessageBox.warning(self, "Uyarı", f"Bu telefon numarası ({phone}) başka bir kişiye ait ({existing.name}).")
            self.le_phone.setFocus()
            return

        try:
            if not self.person:
                self.person = Person()
                self.session.add(self.person)

            self.person.name = name
            self.person.tc_no = tc if tc else None
            self.person.title = self.le_title.text().strip() or None
            self.person.phone = phone
            self.person.email = self.le_email.text().strip() or None
            self.person.address = self.le_address.toPlainText().strip() or None
            self.person.notes = self.te_notes.toPlainText().strip() or None
            self.person.is_active = self.chk_active.isChecked()

            self.session.commit()
            self.accept()
        except Exception as e:
            self.session.rollback()
            QMessageBox.critical(self, "Hata", f"Kayıt kaydedilirken hata oluştu:\n{e}")


class PersonsPage(QWidget):
    def __init__(self, session, user):
        super().__init__()
        self.session = session
        self.user = user
        self._all = []
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        # Üst Araç Çubuğu
        top_bar = QHBoxLayout()

        self.le_search = QLineEdit()
        self.le_search.setPlaceholderText("🔍 İsim, telefon, TC, e-posta ara...")
        self.le_search.setMinimumWidth(280)
        self.le_search.textChanged.connect(self._filter)
        top_bar.addWidget(self.le_search)

        top_bar.addStretch()

        self.stats_label = QLabel("Toplam: 0 kişi")
        self.stats_label.setStyleSheet("color: #718096; font-size: 12px; font-weight: 500;")
        top_bar.addWidget(self.stats_label)

        if getattr(self.user.role, 'can_create', True):
            btn_add = btn("+ Yeni Kişi", "primary")
            btn_add.clicked.connect(self._add)
            top_bar.addWidget(btn_add)

        layout.addLayout(top_bar)

        # Tablo
        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            "ID", "Ad Soyad", "Ünvan", "Telefon", "E-Posta", "TC No", "Durum", "İşlemler"
        ])
        hh = self.table.horizontalHeader()
        hh.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        hh.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        hh.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        hh.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        hh.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(7, QHeaderView.ResizeMode.ResizeToContents)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.doubleClicked.connect(lambda idx: self._edit(self._all[idx.row()]) if idx.row() < len(self._all) else None)
        layout.addWidget(self.table)

    def refresh(self):
        self._all = self.session.query(Person).order_by(Person.name.asc()).all()
        self._populate(self._all)

    def _filter(self):
        txt = self.le_search.text().strip()
        if not txt:
            filtered = self._all
        else:
            filtered = [
                p for p in self._all
                if tr_contains(txt, p.name)
                or tr_contains(txt, p.phone)
                or tr_contains(txt, p.email)
                or tr_contains(txt, p.tc_no)
                or tr_contains(txt, p.title)
            ]
        self._populate(filtered)

    def _populate(self, persons):
        self.table.setRowCount(len(persons))
        self.stats_label.setText(f"Toplam: {len(persons)} kişi")

        for row, p in enumerate(persons):
            self.table.setRowHeight(row, 40)

            # ID
            item_id = QTableWidgetItem(str(p.id))
            item_id.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 0, item_id)

            # Ad Soyad
            item_name = QTableWidgetItem(p.name or "")
            item_name.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            self.table.setItem(row, 1, item_name)

            # Ünvan
            self.table.setItem(row, 2, QTableWidgetItem(p.title or "—"))

            # Telefon
            item_phone = QTableWidgetItem(p.phone or "—")
            item_phone.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 3, item_phone)

            # E-Posta
            self.table.setItem(row, 4, QTableWidgetItem(p.email or "—"))

            # TC No
            item_tc = QTableWidgetItem(p.tc_no or "—")
            item_tc.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 5, item_tc)

            # Durum
            status_text = "Aktif" if p.is_active else "Pasif"
            item_status = QTableWidgetItem(status_text)
            item_status.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            if p.is_active:
                item_status.setForeground(QColor("#10b981"))
            else:
                item_status.setForeground(QColor("#ef4444"))
            self.table.setItem(row, 6, item_status)

            # İşlemler
            btn_cell = QWidget()
            b_layout = QHBoxLayout(btn_cell)
            b_layout.setContentsMargins(4, 4, 4, 4)
            b_layout.setSpacing(6)

            if getattr(self.user.role, 'can_edit', True):
                b_edit = btn("Düzenle", "secondary", height=28, width=85)
                b_edit.clicked.connect(lambda _, person=p: self._edit(person))
                b_layout.addWidget(b_edit)

            self.table.setCellWidget(row, 7, btn_cell)

    def _add(self):
        dlg = PersonDialog(self.session, self.user, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.refresh()

    def _edit(self, person):
        dlg = PersonDialog(self.session, self.user, person=person, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.refresh()
