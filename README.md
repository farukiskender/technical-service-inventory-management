# Teknik Servis ve Stok Yönetim Sistemi

PyQt6 ve SQLAlchemy 2.0 tabanlı, kurumsal seviyede **Stok Yönetimi**, **Seri Numarası Takibi** ve **Teknik Servis Süreç Yönetimi** masaüstü uygulamasıdır.

Çift modüllü (Yönetici Paneli & Personel İstemcisi) mimarisiyle depolar arası transferleri, dinamik stok hesaplamalarını, seri numaralı parça giriş/çıkışlarını ve teknik servis iş akışını uçtan uca otomatikleştirir.

---

## 📸 Ekran Görüntüleri

| Ana Sayfa & Dashboard | Teknik Servis Yönetimi |
|:---:|:---:|
| ![Dashboard](screenshots/02_dashboard.png) | ![Teknik Servis](screenshots/03_service.png) |

| Servis Detay & Parça Yönetimi | Stok Yönetimi |
|:---:|:---:|
| ![Servis Detayı](screenshots/04_service_detail.png) | ![Stok](screenshots/05_stock.png) |

| Ürün Tanımları | Müşteri & Kişiler |
|:---:|:---:|
| ![Ürünler](screenshots/06_products.png) | ![Müşteriler](screenshots/07_persons.png) |

| Admin Paneli & DB Kurulumu | Kullanıcı Giriş Ekranı |
|:---:|:---:|
| ![Admin](screenshots/08_admin.png) | ![Giriş](screenshots/01_login.png) |

---

## 🚀 Öne Çıkan Özellikler

### 1. Çift Uygulamalı Mimari
- **Admin Paneli (`admin_app`):** İlk kurulum sihirbazı (Setup Wizard), veritabanı motoru seçimi (SQLite / PostgreSQL / MSSQL), kullanıcı, rol ve yetki yönetimi (`can_create`, `can_edit`, `can_delete`, `can_manage`), depo tanımları.
- **Kullanıcı Uygulaması (`main_app`):** Güvenli giriş, interaktif dashboard, stok yönetimi, ürün katalogları, teknik servis süreçleri ve müşteri rehberi.

### 2. Dinamik ve Güvenilir Stok Takibi
- Stok sayıları statik sütunlarda saklanmaz; `StockMovement` (IN, OUT, TRANSFER_IN, TRANSFER_OUT, SERVICE_OUT) hareketlerinin toplanmasıyla **dinamik olarak hesaplanır**.
- Veri tutarsızlığı veya eşzamanlı işlem hataları engellenir.

### 3. Seri Numarası Yönetimi
- `serial_tracking` aktif ürünlerde:
  - **Stok Girişinde:** Miktar kadar seri numarasının toplu girilmesi zorunludur.
  - **Stok Çıkışında ve Serviste:** Depodaki uygun (`available`) seri numaralarından seçim zorunludur. Parça çıkışı yapıldığında durum `used` olarak kilitlenir; işlem iptal edilirse otomatik iade edilir.

### 4. Teknik Servis Otomasyonu
- **Otomatik Servis Numarası:** `SRV-00001` formatında sıralı ve tekil kayıt.
- **Durum ve Süreç Takibi:** `Kayıt Alındı` → `İncelemede` → `Onay Bekliyor` → `Onarıldı` → `Teslim Edildi`.
- **Tarihçe Logu:** Her aşama değişimi ve teknisyen müdahalesi `ServiceHistory` tablosuna zaman damgası ve kullanıcı bilgisiyle kaydedilir.
- **Yedek Parça Entegrasyonu:** Servise eklenen parçalar doğrudan ilgili depodan düşülür (`SERVICE_OUT`), seri numarası varsa kilitlenir.
- **Teslimat Protokolü:** Cihaz teslim edilirken teslim alan müşteri ve teslim eden teknisyen bilgileri kayıt altına alınır.

### 5. Çoklu Veritabanı Desteği
- **SQLite:** Dosya tabanlı, sıfır konfigürasyonla anında çalışma.
- **PostgreSQL:** Kurumsal ağlar ve çok kullanıcılı yapılar için tam destek.
- **MSSQL (SQL Server):** ODBC sürücüsüyle kurumsal Microsoft ekosistemine uyumlu.

### 6. Türkçe Karakter Uyumu ve Ergonomi
- Arama ve filtrelerde Türkçe karakter normalizasyonu (`ı/i`, `İ/i`, `ş/s`, `ç/c`, `ö/o`, `ü/u`, `ğ/g` çift yönlü tolerans).
- Linux / GTK ve Windows tema çakışmalarını engelleyen Fusion tabanlı standart UI.

---

## 🛠️ Kurulum

### 1. Depoyu Klonlayın
```bash
git clone https://github.com/KULLANICI_ADI/teknik-servis-stok-yonetimi.git
cd teknik-servis-stok-yonetimi
```

### 2. Sanal Ortam Oluşturun ve Aktif Edin
```bash
python -m venv venv

# Windows:
venv\Scripts\activate

# Linux / macOS:
source venv/bin/activate
```

### 3. Gereksinimleri Yükleyin
```bash
pip install -r requirements.txt
```

---

## 🏁 Başlatma

### Windows
- **Admin Paneli:** `Admin_Baslat.bat` veya `python admin_app/main.py`
- **Ana Uygulama:** `Uygulama_Baslat.bat` veya `python main_app/main.py`

### Linux / macOS
```bash
chmod +x admin_baslat.sh uygulama_baslat.sh

# Admin Paneli:
./admin_baslat.sh

# Ana Uygulama:
./uygulama_baslat.sh
```

---

## 🔑 Varsayılan Giriş Bilgileri

Sıfır kurulumda varsayılan yönetici hesabı:
- **Kullanıcı Adı:** `admin`
- **Şifre:** `1234`

> İlk girişten sonra Admin Paneli üzerinden şifrenizi değiştirmeniz veya yeni kullanıcılar eklemeniz önerilir.

---

## 🧪 Demo Verileri Yükleme (Opsiyonel)

Uygulamayı test etmek için hazır ürünler, müşteriler ve örnek servis kayıtları oluşturmak isterseniz:
```bash
python seed_demo.py
```

---

## 📂 Proje Yapısı

```text
├── admin_app/              # Yönetici Paneli & Kurulum Sihirbazı
│   ├── main.py             # Admin giriş noktası, DB/Kullanıcı/Depo yönetimi
│   └── __init__.py
├── main_app/               # Ana Kullanıcı (Personel) Uygulaması
│   ├── login.py            # Giriş ekranı ve kimlik doğrulama
│   ├── main.py             # Uygulama giriş noktası
│   ├── main_window.py      # Dashboard ve ana navigasyon iskeleti
│   └── ui/                 # Sayfa modülleri
│       ├── stock_page.py   # Stok hareketleri ve seri no diyalogları
│       ├── service_page.py # Teknik servis ve yedek parça yönetimi
│       ├── products_page.py# Ürün katalog yönetimi
│       └── persons_page.py # Müşteri ve kişi yönetimi
├── shared/                 # Ortak Katman
│   ├── schema.py           # SQLAlchemy ORM modelleri ve DB bağlantı havuzu
│   ├── utils.py            # Türkçe normalizasyon ve arama yardımcıları
│   └── db_config.json      # Aktif DB bağlantı yapılandırması
├── screenshots/            # Uygulama içi ekran görüntüleri
├── seed_demo.py            # Örnek test verisi yükleyici
├── requirements.txt        # Python bağımlılıkları
├── Admin_Baslat.bat        # Windows Admin başlatıcı
└── Uygulama_Baslat.bat     # Windows Ana Uygulama başlatıcı
```

---

## 📄 Lisans
Bu proje MIT lisansı altında sunulmaktadır.
