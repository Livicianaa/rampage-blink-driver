# Özellik envanteri ve RE durumu

Kaynak: orijinal "Gaming Mouse 3.0" uygulamasının skin/dil dosyaları (UI envanteri) ve
`apply_all` yazıcı fonksiyonunun decompile'ı (protokol). Her satırın durumu:
`[ ]` çözülmedi · `[~]` kısmen/statik çözüldü, donanımda doğrulanmadı · `[x]` donanımda doğrulandı.

Config belleği doğrusal; 8 byte'lık bloklarla yazılır/okunur (`blink/device.py`: `read_block`, `write_block`, `apply`).

## 1. Performans sekmesi
- [x] DPI kademeleri: 6 kademe, her biri 5-bit donanım CPI kodu (blok `0x10`), aktif kademe + açık/kapalı maskesi (blok `0x18`)
- [x] CPI kodu -> gerçek CPI tablosu [Kesin]: exe `fcn.00420190` (@ `0x421450`) sensör tablosuyla 12800'e kadar tüm 23 donanım kademesi birebir çözüldü:
  1=200, 2=400, 3=600, 4=800, 5=1000, 6=1200, 7=1400, 8=1600, 9=1800, 0xa=2000, 0xc=2400, 0xd=3200, 0xe=4000, 0xf=4800, 0x10=5600, 0x11=6400, 0x12=7200, 0x13=8000, 0x14=8800, 0x15=9600, 0x16=10400, 0x17=11200, 0x18=12800.
- [x] Çift tık / ateş tuşu hızı (FIRE_TIME, 10..300 ms): blok `0x18` byte2..3 (16-bit). GUI ve CLI eklendi.
- [x] Tarama (polling) hızı: blok `0x18` byte6 (adres `0x1e`) = `1000/Hz - 1`: 1000->0x00, 500->0x01, 250->0x03, 125->0x07. 1000 Hz ve 125 Hz ölçümle doğrulandı (1001 ve 126 rapor/sn); 250/500 formül gereği. Araçlar: `blinkctl.py setpoll`, `poll_olc.py`
- Tekerlek hızı ve "Mouse Sensitivity" (DPI_SPEED): **fare belleğinde değil, host (OS) ayarı**. Orijinal uygulama fareye uygula bittikten sonra Windows `SystemParametersInfo` çağırıyor (imleç hızı 1..20, tekerlek satır sayısı). Linux'ta isteğe bağlı "Sistem" sekmesi: Hyprland `sensitivity` / `scroll_factor`. Globaller: DPI_SPEED 0x656dc9, WHEEL_SPEED 0x656dca, USB_SPEED 0x656dcb, FIRE_TIME 0x650058
- [ ] DPI kademe gösterge rengi (kademe başına R/G/B): bloklar `0x20..0x37`
- [ ] "Mouse Sensitivity" (DPI_SPEED, 11 kademe): fare içi mi, Windows imleç hızı mı belirsiz (muhtemelen sadece host tarafı)

## 2. LED sekmesi
Durum: protokol statik çözüldü, **bu ünitede fiziksel doğrulama yapılamadı**: faren hiç ışık vermiyor.
Denenen: blok `0x18` byte4 (`0x1c`, efekt) ve blok `0x38` byte7 (`0x3f`, parlaklık) farklı değerlerle, ayrıca canlı `0x13` önizleme paketi; hiçbirinde ışık yok. Değişiklikler geri alındı.
- Efekt alanı: blok `0x18` byte4 = `0x80 | (mod&7)<<4 | bayrak<<3 | hız&7`; "LED kapalı"da alt 3 bit 7. Fabrika değeri `0x87`.
- Parlaklık: blok `0x38` byte7 üst nibble (bit 6:4); tek renk: byte6 = `(R<<4)|G`, byte7 alt nibble = B.
- Global adresler: `LED_TYPE`=0x656dce, `LED_CYCTIME`=0x656dcf, `LED_BRIGHT`=0x656fa4, `LED_FEATURE_SYMMETRY`=0x656f9c, `LED_FEATURE_DIREC`=0x656fa0, `LED_FEATURE_SCOLOR`=0x656f98.
- Canlı önizleme paketi (`0x13`, uygulamanın LED testi): `07 13 80 a1 1a 07 03 ff` = efekt sabit, tüm bölgeler.
- [~] 16 efekt: DPI nefes, döngü nefes, sabit, akan su, tek lamba su, kuyruklu yıldız, neon, ışıltı, titreşim, yıldız yolu, dalga, coşkulu, tuş tepkisi, kapalı, tek renk nefes, renk döngüsü
- [ ] Renk döngüsü: 7 renk, her biri aç/kapa (`LED_USER0..5`, `COLn_IN_CYC`)
- [ ] Parlaklık (`LED_BRIGHT`) ve hız (`LED_CYCTIME`)
- [ ] Simetri, akış yönü (saat yönü / ters / çift yön / üstüne yaz)
- [ ] Tuş başına tepki: 9 tuş × (aç/kapa + tepki tipi)
- [ ] Müzikli ışık (Wave / Flicker / Starlight): host tarafında ses analizi, fareye canlı LED komutu (muhtemelen `0x13`)

## 3. Tuş sekmesi
GUI durumu: `gui.py` Tuşlar sekmesi hazır (profil 0, 5 tuş, fonksiyon 1..5, "en az bir sol tık" kuralı, yazma sonrası geri okuma doğrulaması, yazmadan önce otomatik yedek). Katman: `blink/keys.py`. Diğer fonksiyonlar (medya, kısayol, makro, ateş, profil) `blinkctl.py fnscan` ile ölçülüp eklenecek.
Varsayılan profil kuralı: fare üzerinde donanımsal DPI tuşu/fonksiyonu yerine tüm tuşlar genel kullanım için atanabilir; atamalar uygulama üzerinden yönetilir.
Doğrulama seviyesi:
- [x] KESİN (fiziksel test): adres `0x0b` (slot 4) arka yan tuşu kontrol eder; tuş baytı biçimi `0x20 | fonksiyon`; fonksiyon 1 = sol tık (arka tuşa `0x21` yazınca `BTN_LEFT` verdi). Blok `0x00` VID/PID (`0x30fa`/`0x1440`) USB kimliğiyle eşleşiyor.
- [x] KESİN (`blinkctl.py slotmap`, 4 slot rehberli test): slot 2 (`0x09`) = orta tuş, slot 3 (`0x0a`) = sağ, slot 4 (`0x0b`) = arka yan, slot 5 (`0x0c`) = ön yan; slot 1 (`0x08`) = sol (elenerek). Fonksiyon 1..5 = sol, orta, sağ, geri (`BTN_SIDE`), ileri (`BTN_EXTRA`). Slotlar fabrika `21 22 23 24 25`.
- [~] MUHTEMEL (statik çıkarım + dump tutarlılığı, test EDİLMEDİ): aktif profil = blok `0x00` byte1 bit5-6; profil tabloları (slot s 1-tabanlı): profil 0 `0x08 + s-1` (s=1..9), s=10..12 -> `0x3b..0x3d`; profil 1 `0x44 + s-1`; profil 2 `0x50 + s-1`; profil 3 `0x60 + s-1`.
- [x] KESİN (`blinkctl.py fnprobe`, el sallama sayacı + olay izleme, 2026-10-21): fonksiyon `0x06` (DPI döngüsü), `0x0b`, `0x0c` atanmış tuşa basınca Linux'a hiç tuş olayı gelmez (fare tuşu içeride tüketir) ve DPI düşer (B/A oranı 0,37 / 0,27 / 0,54; A 11k-20k, B 4k-8k). İmleç hareketlerinde DPI değişimi doğrulandı. Aynı testin otomatik kararı 0x0c için yanlış çıktı (eşik gürültüye göre sıkıydı), düzeltildi.
- [~] 0x0b = DPI+ ve 0x0c = DPI-: yön DOĞRULANMADI (test sadece iki kademeyle, üst kademeden başlayıp yapıldı, ikisi de aşağı gitmiş olabilir). Yön testi için üç kademe aç (örn. 0, 2, 5), orta kademeden başla.
- [x] KESİN (RE Decompile, 2026-10-23): slot 9 (adres `0x10`, `0x26`) = fiziksel DPI tuşu; UI fonksiyon -> cihaz kodu:
  - UI 1..6 -> 1..6 (Sol, Orta, Sağ, Geri, İleri, DPI döngüsü)
  - UI 14 (Ateş) -> 9 (`0x09`), FIRE_TIME gecikmesi blok 0x18 byte2..3
  - UI 16 (DPI+) -> 11 (`0x0b`), UI 17 (DPI-) -> 12 (`0x0c`)
  - UI 19 (LED Switch) -> 23 (`0x17`)
  - UI 30001 (0x7531, Devre Dışı) -> 0 (`0x00`)
  - UI 40000 (PUBG geri tepme modu) -> 22 (`0x16`)
  - Medya Tuşları (UI 23..33): HID Consumer Usage kodları: Web (0x223), Medya (0x183), Mail (0x18a), Vol+ (0xe9), Vol- (0xea), Prev (0xb6), Next (0xb5), Mute (0xe2), Play/Pause (0xcd), Calc (0x192), Stop (0xb7).
  - Kısayol Tuşları: Windows Virtual Key kodları (`fcn.00428e20` tablosu) + Ctrl/Alt/Shift/Win bayrakları.
- Not: "yan tuşları takas" testi sonuçsuz kaldı, kanıt sayılmaz. Bayt `bit5` (0x20) fabrika tuşlarında hep 1.
- [ ] 9 tuş slotu × 4 profil, tuş başına 1 byte (bayrak<<6 + değer<<5 + kod), `apply_all` satır ~372-630
- [ ] Fonksiyonlar: sol/orta/sağ tık, geri, ileri, DPI döngüsü (DPI+/DPI-), genişletilmiş, medya, makro, kısayol, profil seçimi, ateş, LED anahtarı
- [ ] Kısayol: Ctrl/Shift/Alt/Win + klavye tuşu (kısayol bloğu `0x2e4*4` bayt yapıları)
- [ ] Medya tuşları (Consumer usage)
- [ ] Kural: en az bir tuş "sol tık" olmalı
- [ ] Profil seçimi tuşu

## 4. Profiller
- [ ] 4 profil (Ofis, Oyun I, II, III), aktif profil seçimi
- [ ] İçe/dışa aktarma ve sıfırlama (uygulama tarafı: kendi JSON formatımız)

## 5. Makro sekmesi
Statik bulgular [Kesin, 2026-10-23, `apply_all.c` satır ~1440-2050]:
- Tanımlayıcı Tablosu: Adres `0xa0`'dan başlayan 560 bayt (70 blok × 8 bayt). 4 profil × 14 tuş slotu için 10 baytlık descriptor yapısı.
  - Byte 0: Zaman çözünürlüğü böleni - 1 (`0x65003c - 1`)
  - Byte 1: Tekrar modu (bit 7 = tekrar tipi, alt 7 bit = süre/uzunluk). Mod 1: Tuş basılı kaldıkça, Mod 2: Toggle, Mod 4: N defa.
  - Byte 2..4: Olay adetleri ve ofsetler
  - Byte 5..7: Makro veri alanındaki doğrusal bayt ofseti
  - Byte 8: Tekrar sayısı (16-bit repeat count)
  - Byte 9: 0 sabit
- Başlıklar: `0x6e` (2 bayt, makro alanı başlangıç ofseti), `0x70` (8 bayt, bölüm sınırları).
- Olay Akışı (Event Stream):
  - Klavye tuşu bas: `[gecikme | 0x80, keycode]` (2 bayt).
  - Klavye tuşu bırak: `[gecikme & 0x7F, keycode]` (2 bayt).
  - Fare bağıl hareketi (XY): `[gecikme, 0xF6, dx_lo, dx_hi, dy_lo, dy_hi]` (6 bayt, 16-bit signed).
  - DPI değişimi: `[gecikme | flag, 0xF8, dpi_kodu, 0]` (4 bayt).
  - LED değişimi: `[gecikme, 0xF9, ...]`
  - Gecikme bölme: 127'yi (0x7F) aşan gecikmeler `[0x7F, 0x00]` parçaları olarak eklenir.
- Yazılımsal vs Donanımsal:
  - `config.ini` içinde `SOFT_HARD_MAC=0` bulunur. Windows yazılımı tuş basıldığında vendor paketinden (`0x660913 == 0xf0 + key`) host-side işletim de yapar (`fcn.0042d80f`).
  - Linux kontrol aracımız için ilk etapta en güvenli ve esnek yol: Host-side (evdev + uinput), donanımsal makro yazma ise deneysel/isteğe bağlı tutulabilir.
- [ ] Makro grupları (en çok 12), grup başına makrolar
- [ ] Olaylar: tuş bas/bırak, fare tuşları, XY hareketi (4 yön), DPI ayarla/sıfırla, LED, gecikme
- [ ] Tekrar modları: tuş basılı kaldıkça / tekrar basılana dek / N kez
- [ ] Kayıt (record), içe/dışa aktarma (şifreli dışa aktarma da var)
- [ ] PUBG geri tepme telafisi ("gun"): `PUBG.dat` ön tanımlı makrolar, parametreler: baskı aralığı, gecikme, tekrar, ateş modu
- [ ] Tuş 1'in makroya çevrilmesi

## 6. Diğer
- [ ] 28 dil (uygulama tarafı, bizde ayrı i18n)
- [ ] Config import/export/reset (uygulama tarafı)

## RE sırası
1. Performans: polling, tekerlek, ateş zamanı, gösterge renkleri (blok `0x18`, `0x20..`)
2. LED
3. Tuşlar + profiller
4. Makro (en büyük)
5. Müzikli ışık

Doğrulama yöntemi: her alan için statik paketleme -> okunan canlı dump ile karşılaştırma -> yedek alarak oku-değiştir-yaz -> fiziksel gözlem.
