"""
Demo Veri Yükleyici — Teknik Servis ve Stok Yönetim Sistemi
Geliştirme ve test amaçlı örnek ürün, müşteri ve servis kayıtları oluşturur.
"""

import sys
import os
import bcrypt
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from shared.schema import (
    load_db_config, get_engine, get_session_factory, Base,
    Role, User, Person, Product, Warehouse, StockMovement, SerialNumber, ServiceRecord, ServiceHistory
)


def seed_demo_data():
    config = load_db_config()
    if not config:
        print("[Hata] db_config.json bulunamadı. Lütfen önce Admin uygulamasını çalıştırın.")
        return

    engine = get_engine(config)
    Session = get_session_factory(engine)
    session = Session()

    print("[1/5] Varsayılan Rol ve Kullanıcılar oluşturuluyor...")
    admin_role = session.query(Role).filter_by(name="Yönetici").first()
    if not admin_role:
        admin_role = Role(name="Yönetici", can_view=True, can_create=True, can_edit=True, can_delete=True, can_manage=True)
        session.add(admin_role)
        session.commit()

    admin_user = session.query(User).filter_by(username="admin").first()
    if not admin_user:
        pw_hash = bcrypt.hashpw("1234".encode(), bcrypt.gensalt()).decode()
        admin_user = User(
            username="admin",
            password_hash=pw_hash,
            full_name="Sistem Yöneticisi",
            title="Baş Teknisyen",
            role_id=admin_role.id,
            is_active=True
        )
        session.add(admin_user)
        session.commit()

    print("[2/5] Depolar oluşturuluyor...")
    wh_main = session.query(Warehouse).filter_by(name="Merkez Depo").first()
    if not wh_main:
        wh_main = Warehouse(name="Merkez Depo", location="A Blok Zemin Kat", description="Ana Depolama Alanı", is_active=True)
        session.add(wh_main)

    wh_srv = session.query(Warehouse).filter_by(name="Servis Deposu").first()
    if not wh_srv:
        wh_srv = Warehouse(name="Servis Deposu", location="B Blok 1. Kat", description="Yedek Parça ve Servis Deposu", is_active=True)
        session.add(wh_srv)

    session.commit()

    print("[3/5] Örnek Ürünler ve Seri Numaraları ekleniyor...")
    sample_products = [
        ("PRD-001", "Corsair Vengeance 16GB DDR4 RAM", "Elektronik", "Adet", True, 20),
        ("PRD-002", "Samsung 980 PRO 1TB NVMe M.2 SSD", "Elektronik", "Adet", True, 15),
        ("PRD-003", "Western Digital 1TB SATA SSD", "Elektronik", "Adet", True, 10),
        ("PRD-004", "Termal Macun Arctic MX-4 4g", "Sarf Malzeme", "Adet", False, 50),
        ("PRD-005", "HDMI 2.1 Örgülü Kablo 2m", "Aksesuar", "Adet", False, 40),
        ("PRD-006", "Lehim Teli 0.8mm 200g", "Sarf Malzeme", "Rulo", False, 25),
        ("PRD-007", "Dell Type-C 65W Şarj Adaptörü", "Yedek Parça", "Adet", True, 12),
        ("PRD-008", "HP 15-DW Laptop Klavyesi (TR)", "Yedek Parça", "Adet", True, 8),
    ]

    for code, name, cat, unit, serial_trk, initial_qty in sample_products:
        p = session.query(Product).filter_by(product_code=code).first()
        if not p:
            p = Product(
                product_code=code,
                name=name,
                category=cat,
                unit=unit,
                serial_tracking=serial_trk,
                is_active=True
            )
            session.add(p)
            session.flush()

            serials = []
            if serial_trk:
                for i in range(1, initial_qty + 1):
                    s_no = f"{code[:3]}-{datetime.now().year}-{p.id:02d}-{i:04d}"
                    sn_obj = SerialNumber(
                        product_id=p.id,
                        warehouse_id=wh_main.id,
                        serial_no=s_no,
                        status="available"
                    )
                    session.add(sn_obj)
                    serials.append(s_no)

            mv = StockMovement(
                product_id=p.id,
                warehouse_id=wh_main.id,
                movement_type="IN",
                quantity=float(initial_qty),
                serial_numbers_json=serials if serials else None,
                reason="İlk Stok Açılışı",
                reference_type="MANUAL",
                user_id=admin_user.id
            )
            session.add(mv)

    session.commit()

    print("[4/5] Örnek Müşteriler ekleniyor...")
    sample_persons = [
        ("Ahmet Yılmaz", "0532 100 2030", "ahmet.yilmaz@email.com", "Bilişim Uzmanı", "Kadıköy / İstanbul"),
        ("Ayşe Kaya", "0544 200 3040", "ayse.kaya@email.com", "Mimar", "Çankaya / Ankara"),
        ("Mehmet Demir", "0555 300 4050", "mehmet.demir@email.com", "Firma Sahibi", "Nilüfer / Bursa"),
        ("Zeynep Çelik", "0505 400 5060", "zeynep.celik@email.com", "Grafiker", "Konak / İzmir"),
    ]

    for name, phone, email, title, addr in sample_persons:
        person = session.query(Person).filter_by(phone=phone).first()
        if not person:
            person = Person(
                name=name,
                phone=phone,
                email=email,
                title=title,
                address=addr,
                is_active=True
            )
            session.add(person)

    session.commit()

    print("[5/5] Örnek Servis Kayıtları oluşturuluyor...")
    p1 = session.query(Person).first()
    if p1 and not session.query(ServiceRecord).first():
        srv1 = ServiceRecord(
            service_no="SRV-00001",
            person_id=p1.id,
            customer_name=p1.name,
            customer_phone=p1.phone,
            device_info="Dell XPS 15 9500 Laptop",
            device_serial="DLXPS9500-2024",
            complaint="Cihaz aşırı ısınıyor ve yük altında kapanıyor.",
            status="İncelemede",
            received_by=admin_user.full_name,
            delivered_by=p1.name,
            work_done="Fan temizliği yapıldı, termal macun yenileniyor.",
            user_id=admin_user.id
        )
        session.add(srv1)
        session.flush()

        h1 = ServiceHistory(
            service_id=srv1.id,
            user_id=admin_user.id,
            old_status="Kayıt Alındı",
            new_status="İncelemede",
            notes="Teknisyen incelemeye aldı. Termal bakım planlandı."
        )
        session.add(h1)
        session.commit()

    print("\n✓ Demo veri kurulumu başarıyla tamamlandı!")
    print("✓ Giriş Bilgileri: Kullanıcı Adı: admin | Şifre: 1234")


if __name__ == "__main__":
    seed_demo_data()
