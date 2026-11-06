# Teknik Servis ve Stok Yönetim Sistemi — Kapsamlı Onarım ve Geliştirme Planı

## Sorunlar ve İstekler Özeti

Kullanıcı tarafından bildirilen sorunlar ve istekler aşağıda gruplanmıştır:

---

## 1. Kişiler Modülü (persons_page.py + schema.py)

### Sorunlar:
- **Telefon numarası zorunlu değil** — kişi telefon olmadan eklenebiliyor
- **Telefon numarası unique değil** — aynı numaraya 2 kayıt oluşturulabiliyor

### Yeni Özellikler:
- **TC Kimlik No** alanı eklenmeli
- **Ünvan** alanı eklenmeli
- **E-Posta** alanı eklenmeli

### Planlanan Değişiklikler:

#### [MODIFY] [schema.py](file:///home/user/Masaüstü/Yeni%20Klasör/shared/schema.py)
- `Person` modeline yeni alanlar ekle:
  - `tc_no = Column(String(11))` — TC Kimlik No (opsiyonel, 11 haneli)
  - `title = Column(String(200))` — Ünvan
  - `email = Column(String(200))` — E-Posta
- `phone` alanını `nullable=False, unique=True` yap

> [!IMPORTANT]
> Veritabanı zaten mevcut olduğu için, mevcut tabloya migration uygulanmalı. SQLite'da `ALTER TABLE` ile yeni kolonlar eklenecek. `phone` alanındaki UNIQUE constraint ise SQLite'ın ALTER TABLE kısıtlaması nedeniyle mevcut veriler kontrol edilerek uygulama tarafında yönetilecek.

#### [MODIFY] [persons_page.py](file:///home/user/Masaüstü/Yeni%20Klasör/main_app/ui/persons_page.py)
- `PersonDialog` formuna yeni alanlar ekle: TC No, Ünvan, E-Posta
- **Telefon zorunlu** validasyonu: `_save()` metodunda telefon boşsa hata ver
- **Telefon unique** kontrolü: Kayıt sırasında aynı telefon numarasına sahip başka kişi var mı kontrolü
- Tablo sütunlarına TC No, Ünvan, E-Posta ekle
- Arama fonksiyonunda yeni alanlarda da arama yapılabilsin

---

## 2. Servis Modülü (service_page.py + schema.py)

### Sorunlar:
- **Şikayet alanı çok küçük** — `setMaximumHeight(80)` kaldırılarak büyütülecek
- **Servis detay diyaloğu crash veriyor** — `ServiceDetailDialog._build_ui()` içinde relationship'lerin lazy load sorunu; `ServiceHistory.user` ilişkisi tanımlı değil
- **Ürün ekleme kayıt oluşturma sırasında olmamalı** — Form diyaloğundan ürün ekleme bölümü kaldırılacak; ürün ekleme sadece detay ekranından yapılacak

### Yeni Özellikler:
- **Teslim Eden / Teslim Alan** alanları: hem kayıt oluşturma hem de teslim aşamasında sorulacak
- **Yapılan İşlem** alanı: servis kaydı detayında görüntülenecek

### Planlanan Değişiklikler:

#### [MODIFY] [schema.py](file:///home/user/Masaüstü/Yeni%20Klasör/shared/schema.py)
- `ServiceRecord` modeline yeni alanlar ekle:
  - `delivered_by = Column(String(200))` — Teslim Eden (cihazı servise getiren kişi)
  - `received_by = Column(String(200))` — Teslim Alan (servis personeli)
  - `delivered_to = Column(String(200))` — Teslim Edilen Kişi (teslim aşamasında)
  - `received_from = Column(String(200))` — Teslim Alınan Kişi (teslim aşamasında)
  - `work_done = Column(Text)` — Yapılan İşlem
- `ServiceHistory` modeline `user` relationship'i ekle (crash sebebi)

#### [MODIFY] [service_page.py](file:///home/user/Masaüstü/Yeni%20Klasör/main_app/ui/service_page.py)

**ServiceFormDialog:**
- `te_complaint` maksimum yükseklik kısıtlamasını `setMaximumHeight(80)` → `setMinimumHeight(120)` olarak değiştir
- Ürün ekleme bölümünü (`items_group`) tamamen **kaldır** — yeni kayıt formundan çıkar
- Kayıt formuna "Teslim Eden" ve "Teslim Alan" alanlarını ekle
- `_save()` metodundan ürün işlem kodlarını kaldır

**ServiceDetailDialog:**
- **Crash fix:** `ServiceHistory` → `user` erişimi güvenli hale getir (`h.user_id` ve relationship kontrolleri)
- Detay ekranına **ürün ekleme** bölümü ekle (kayıt sonrası ürün ekleme burada yapılacak)
- Detay ekranına "Yapılan İşlem" alanı ekle
- Teslim eden/alan bilgilerini göster
- Teslim aşamasında (durum "Teslim Edildi" olduğunda) teslim bilgisi sorulacak

---

## 3. Stok Modülü (stock_page.py)

### Sorunlar:
- **Stok detay diyaloğu crash veriyor** — `ProductStockDetailDialog` içinde `sn.warehouse` lazy-load hatası; `SerialNumber` modelinde `warehouse` relationship'i tanımlı değil

### Planlanan Değişiklikler:

#### [MODIFY] [schema.py](file:///home/user/Masaüstü/Yeni%20Klasör/shared/schema.py)
- `SerialNumber` modeline `warehouse` relationship'i ekle:
  ```python
  warehouse = relationship("Warehouse")
  ```

#### [MODIFY] [stock_page.py](file:///home/user/Masaüstü/Yeni%20Klasör/main_app/ui/stock_page.py)
- `ProductStockDetailDialog` içinde `sn.warehouse` erişimini güvenli hale getir (fallback kontrolü)

---

## 4. Veritabanı Migrasyonu

SQLite'ın `ALTER TABLE` kısıtlamaları nedeniyle, mevcut veritabanına yeni sütunlar eklemek için bir migration mekanizması gerekiyor.

#### [MODIFY] [schema.py](file:///home/user/Masaüstü/Yeni%20Klasör/shared/schema.py)
- `create_all_tables` fonksiyonunun yanına bir `migrate_database(engine)` fonksiyonu ekle
- Bu fonksiyon `ALTER TABLE ... ADD COLUMN` komutlarıyla eksik sütunları güvenli şekilde ekleyecek
- Uygulama başlatıldığında otomatik çalışacak

---

## Değişiklik Özeti (Dosya bazlı)

| Dosya | Değişiklik Türü | Açıklama |
|-------|-----------------|----------|
| `shared/schema.py` | MODIFY | Person'a TC/ünvan/e-posta, ServiceRecord'a teslim alanları, ServiceHistory'e user relationship, SerialNumber'a warehouse relationship, migration fonksiyonu |
| `main_app/ui/persons_page.py` | MODIFY | Yeni form alanları, telefon zorunlu+unique validasyonu, tablo sütunları |
| `main_app/ui/service_page.py` | MODIFY | Şikayet alanı büyütme, ürün eklemeyi formdan kaldır, detay crash fix, detaya ürün ekleme taşı, teslim alanları |
| `main_app/ui/stock_page.py` | MODIFY | Stok detay crash fix |
| `main_app/login.py` | MODIFY | Migration fonksiyonunu uygulama başlangıcında çağır |

---

## Verification Plan

### Manual Verification
1. Uygulamayı başlat ve kişi ekleme formunda:
   - Telefonsuz kayıt eklemeyi dene (engellenmelidir)
   - Aynı telefon numarasıyla 2 kişi eklemeyi dene (engellenmelidir)
   - TC No, Ünvan, E-Posta alanlarını doldurarak kayıt ekle
2. Servis kaydı oluştur:
   - Şikayet alanının geniş olduğunu kontrol et
   - Ürün ekleme bölümünün kayıt formunda olmadığını doğrula
   - Teslim eden/alan alanlarının mevcut olduğunu doğrula
3. Servis detay ekranını aç:
   - Crash olmadan açılmalı
   - Ürün ekleme bölümünün burada olduğunu doğrula
4. Stok detay ekranını aç:
   - Crash olmadan açılmalı
