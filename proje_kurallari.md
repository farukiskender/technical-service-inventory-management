# Teknik Servis ve Stok Yönetim Sistemi - Proje Kuralları ve Geliştirme Belleği

Bu doküman, yapay zeka asistanları (veya yeni geliştiriciler) için projenin tam bağlamını, mimarisini, kurallarını ve geliştirme sürecinde alınan tasarım kararlarını içerir. **Projeye devam edileceği zaman bu dokümanın okunması, mevcut yapıya uygun kod yazılması için kritik öneme sahiptir.**

## 1. Proje Özeti
Proje, PyQt6 (Arayüz) ve SQLAlchemy (Veritabanı ORM) kullanılarak geliştirilmiş, çift uygulamalı (Admin ve Main) bir Teknik Servis ve Stok Yönetim masaüstü yazılımıdır. 
Amaç: Şirketlerin stoklarını depolara göre takip edebilmesi, seri numarası bazlı giriş/çıkış yapabilmesi ve müşteri cihazlarının teknik servis süreçlerinin aşama aşama (loglu olarak) yönetilebilmesidir.

## 2. Kullanılan Teknolojiler
- **Arayüz:** PyQt6 (Modern, dark/light moda uygun standart widget'lar)
- **Veritabanı:** SQLAlchemy 2.0+ (Şu an SQLite üzerinden çalışıyor ancak PostgreSQL/MySQL gibi DB'lere geçişe hazır)
- **Stil Yönetimi:** Vanilla QSS ve dinamik `setStyleSheet` (İşletim sistemi tema sorunlarını aşmak için)

## 3. Mimari Yapı ve Dizin Dağılımı
Uygulama modüler olarak 3 ana parçaya ayrılmıştır:
```text
Yeni Klasör/
├── shared/             # Her iki uygulamanın ortak kullandığı yapı
│   ├── db.py           # Engine, Session, Init işlemleri
│   └── schema.py       # SQLAlchemy ORM Modelleri (Tablolar)
├── admin_app/          # Yönetici Paneli ve Kurulum Sihirbazı
│   ├── main.py         # Giriş noktası
│   └── ui/             # SetupWizard, Dashboard, Yönetim sekmeleri
├── main_app/           # Son Kullanıcı (Personel) Uygulaması
│   ├── main.py         # Giriş noktası (Login -> MainWindow)
│   ├── login.py        # Kullanıcı giriş ekranı
│   ├── main_window.py  # Sol menülü (Sidebar) ana iskelet
│   └── ui/             # Alt modüller (Ürünler, Stok, Servis, Kişiler vb.)
├── admin_baslat.sh     # Linux başlatma betiği (Admin)
└── uygulama_baslat.sh  # Linux başlatma betiği (Main)
```

## 4. Temel Veritabanı Modelleri (schema.py)
Tüm tablolar `shared/schema.py` içerisindedir.
- **User & Role:** Kullanıcılar ve yetkileri (can_create, can_edit, can_delete).
- **Warehouse:** Depolar. Her stok hareketi bir depoya bağlıdır.
- **Product:** Ürünler. `serial_tracking` (Boolean) alanı, ürünün seri numarası ile takip edilip edilmediğini belirler.
- **StockMovement:** **(KRİTİK)** Stok miktarları statik bir kolonda tutulmaz. Giriş (IN, TRANSFER_IN) ve Çıkış (OUT, TRANSFER_OUT, SERVICE_OUT) hareketlerinin toplanmasıyla *dinamik olarak hesaplanır*.
- **SerialNumber:** `product_id` ve `warehouse_id`'ye bağlıdır. Durumu `available` veya `used` olur.
- **Person:** Müşteriler veya tedarikçiler (Ad, telefon, adres).
- **ServiceRecord & ServiceItem & ServiceHistory:** Servise gelen cihazlar. `ServiceItem`, serviste kullanılan yedek parçaları (stoktan düşülen) temsil eder. `ServiceHistory` durum değişim loglarını tutar.

## 5. Kesin Geliştirme Kuralları (ÖNEMLİ!)

### Kural 1: İşletim Sistemi Tema Çakışmaları ve Buton Stilleri
Linux/GTK ortamlarında, PyQt6 butonlarına `setObjectName` üzerinden atanan standart QSS stilleri (özellikle yazı renkleri) işletim sistemi tarafından ezilmektedir.
**Çözüm/Kural:**
1. Uygulama başlatılırken `app.setStyle("Fusion")` kesinlikle çağrılmalıdır.
2. Renkli butonlar (Kaydet, Sil, İptal vs.) için `main_app/ui/stock_page.py` dosyasındaki `btn(text, variant, height, width)` yardımcı fonksiyonu kullanılmalıdır. Bu fonksiyon, butonun `setStyleSheet` özelliğine doğrudan ve ezilemez şekilde renk, padding, border-radius atar. QSS class'ları (`#btnSuccess` vb.) KULLANILMAMALIDIR.

### Kural 2: Stok Hesaplama Mantığı
Ürünlerin stokunu öğrenmek için `StockMovement` tablosuna sorgu atılır.
Bunun için `main_app.ui.stock_page` içindeki `get_stock_level(session, product_id, warehouse_id)` metodu kullanılır. Stoklar asla manuel olarak bir değişkene yazılıp artırılıp azaltılmaz.

### Kural 3: Seri Numarası Yönetimi Sistemi
Eğer bir ürünün `serial_tracking` değeri `True` ise;
- **Stok Girişinde:** Miktar kadar seri numarasının `SerialEntryDialog` (QTextEdit çoklu satır) üzerinden girilmesi **zorunludur**.
- **Stok Çıkışında/Serviste:** O ürüne ve o depoya ait, durumu `available` olan seri numaraları `SerialSelectDialog` (QListWidget multiple selection) ile seçilmek zorundadır.

### Kural 4: Modüller Arası Bağımlılık
Pencereler `QMainWindow` (MainWindow) içinde `QStackedWidget` kullanılarak sekmeler halinde yönetilir. Bir sekmeden diğerine geçildiğinde verilerin güncellenmesi için `refresh()` metodları çağrılır. (Bkz: `main_window.py` -> `_switch_page`)

## 6. Mevcut Durumda Yapılanlar ve Eklenen Son Özellikler
- Veritabanı ORM yapısı sıfırdan kuruldu ve ilişkiler bağlandı.
- Admin uygulamasında ilk kurulum (Setup Wizard) ile varsayılan depo, rol ve yönetici oluşturma yapıldı.
- Main uygulamada ürün ekleme, kategori seçme (Editable ComboBox eklendi), birim seçme ve ürün açıklaması alanları yapıldı.
- Stok sayfası tasarlandı. Çift tıklayınca açılan `ProductStockDetailDialog` ile ürün detayları, depo bazlı stok sayıları ve boştaki seri numaralarının kalem kalem listelendiği gelişmiş görünüm eklendi.
- Teknik Servis modülü (`service_page.py`) ve Müşteriler/Kişiler modülü (`persons_page.py`) tam entegre edildi:
  - Otomatik servis numarası üretimi (`SRV-00001` formatında).
  - Kayıtlı müşteri seçimi (`SearchableSelector`) veya bağımsız serbest müşteri bilgisi girişi.
  - Servis detay ekranında dinamik yedek parça ekleme/çıkarma (Depo ve seri no takibiyle otomatik `SERVICE_OUT` stok hareketi oluşturulması).
  - Statü ve aşama yönetimi ("Kayıt Alındı", "İncelemede", "Onay Bekliyor", "Onarıldı", "Teslim Edildi", "İptal Edildi").
  - `DeliveryDialog` ile teslim alan/eden ve tarihçe kaydı oluşturma.
  - Yapılan işlem (`work_done`) ve kronolojik durum değişim tarihçesi (`ServiceHistory`).
- Dashboard üzerine Açık Servis ve Müşteri/Kişi istatistik kartları eklendi.
- Buton renk uyumluluğu tüm sayfalarda doğrudan stil enjeksiyonu (`btn` fonksiyonu) yapılarak standartlaştırıldı.

## 7. Sonraki Geliştirmeler İçin Notlar (Kaldığımız Yer)
Yapay zeka asistanına bu dosya verildiğinde, uygulamanın temel UI sorunlarının ve ORM mimarisinin tamamlandığı bilinmelidir. Bundan sonraki olası adımlar şunlar olabilir:
1. Raporlama modülü (Gelişmiş PDF veya Excel çıktıları).
2. Barkod/Karekod oluşturma ve okutma yetenekleri (PyQt6 üzerinde QTimer ve barkod okuyucu klavye emülasyonu entegrasyonu).
3. Müşteriye SMS/E-Posta gönderim entegrasyonları.
4. Dashboard üzerindeki "Son Servisler" gibi alanlara daha fazla grafik veya interaktif veri eklenmesi.

**Mevcut komut:** `python3 main_app/main.py` veya `./uygulama_baslat.sh` ile uygulamayı çalıştırıp kalınan yeri test edebilirsiniz.
