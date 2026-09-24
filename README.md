# AoEM Translator — Discord Çeviri Botu

Age of Empires Mobile (AoEM) Discord sunucuları için çeviri botu. Kanallardaki mesajlara otomatik bayrak tepkisi ekler, bayrağa tıklayınca mesajı o dile çevirir. Çeviri motoru olarak DeepL API Free kullanır (ayda 500.000 karakter, ücretsiz).

---

## 1. Ne yapar?

- **Otomatik bayrak tepkileri:** Seçili kanallardaki her mesajın altına bot kendisi 🌐 + sabit 14 bayrak (🇬🇧 🇹🇷 🇸🇦 🇷🇺 🇪🇸 🇧🇷 🇩🇪 🇫🇷 🇻🇳 🇮🇩 🇨🇳 🇰🇷 🇵🇭 🇯🇵) ekler; liste her sunucuda aynıdır ve değiştirilemez.
- **Bayrağa tıklayınca çeviri:** Bir bayrağa tıklandığında bot mesajı o bayrağın diline çevirip yanıt (reply) olarak yazar. Kaynak dil otomatik algılanır → her dilden her dile çalışır (örn. Portekizce mesaja 🇨🇳 basınca Çince gelir). Otomatik listede olmayan bir bayrağı kullanıcı kendisi bassa da çevirir.
- **🌐 ile kişisel dil — sıfır kurulum:** Dilini henüz seçmemiş bir kullanıcı 🌐 tepkisine tıkladığında bot, mesajın altında tıklanabilir bir dil menüsü açar (en yaygın 25 dil, bayrak etiketli). Menüden bir dil seçmek yeter: seçim o kullanıcı için kalıcı olarak kaydedilir ve mesaj anında seçilen dile çevrilip mesajın altına herkese açık bir reply olarak yazılır — hiçbir komut yazmadan, tek tıkla dil seçimi ve çeviri. Dili daha önce ayarlamış kullanıcılar 🌐'ye tıklayınca çeviriyi doğrudan alır (🌐 için asla DM gönderilmez); mesaja sağ tık → Apps → "Translate to my language" ile de kimseye görünmeyen bir çeviri alır.
- **Admin slash komutları:** Otomatik bayrak kanalları ve tüm ayarlar slash komutlarıyla yönetilir; kod değişikliği gerekmez (bayrak listesi sabittir, komutla değiştirilemez).

## 2. Gereksinimler

- **Python 3.11+** (Windows kurulumunda "Add python.exe to PATH" kutusunu işaretle)
- **Git** (Windows)
- Bir Discord bot uygulaması (aşağıda) ve bir DeepL API Free anahtarı

## 3. Discord Developer Portal ayarları

[discord.com/developers/applications](https://discord.com/developers/applications) adresinde uygulamanı aç:

1. **Message Content Intent AÇIK olmalı:** Bot → Privileged Gateway Intents altında **Message Content Intent** anahtarını aç. Bu izin "privileged"dır; tepki verilen mesajın içeriğini okumak için şarttır. Kapalıysa bot bayrak ekleyebilir ama mesajı **okuyamaz**, dolayısıyla çeviri yapamaz.
2. **Public Bot / Private Bot:** Bot → "Public Bot" anahtarı, botu sadece kendi sunucularına ekleyeceksen **kapalı** olsun; açık olursa davet linki elden ele dolaşabilir. (İkinci katman koruma olarak `.env` içindeki `ALLOWED_GUILD_IDS` kullanılabilir: bot, listede olmayan sunucudan kendiliğinden çıkar.)
3. **Install Link → None:** Installation sekmesinde "Install Link" seçeneğini **None** yap. Discord'un otomatik kurulum bağlantısı yerine aşağıdaki (izinleri sınırlı) davet linkimizi kullanıyoruz.

## 4. DeepL API Free key alma

1. [deepl.com](https://www.deepl.com/pro-api) adresine git ve **DeepL API Free** planına kaydol (ücretsizdir, kredi kartı istemez).
2. Hesap ayarları → Account → **Authentication Key (DeepL API)** anahtarını kopyala.
3. Free anahtarlar `:fx` ile biter; sendeki anahtar `:fx` ile bitmiyorsa yanlışlıkla Pro planı anahtarı almışsındır.
4. Free kota **ayda 500.000 karakter**dir — bu bot için fazlasıyla yeterlidir (kota kullanımını `/stats` ile görebilirsin).
5. Anahtarı `.env` dosyasındaki `DEEPL_API_KEY` satırına yaz. Anahtarı hiçbir dosyaya commit etme, kimseyle paylaşma. Repo GitHub'da **public**tir; `.env`, `data/`, `logs/` asla commit edilmez — repoya giren bir token herkes tarafından okunur ve hemen kötüye kullanılabilir.

## 5. `.env` dosyasını doldurma

`.env.example` dosyasını `.env` olarak kopyala ve değerleri doldur:

| Anahtar | Ne işe yarar |
|---|---|
| `DISCORD_TOKEN` | **Zorunlu.** Developer Portal → Bot → Reset Token ile aldığın bot token'ı. |
| `DEEPL_API_KEY` | **Zorunlu** (`ENGINE=deepl` iken). DeepL API Free anahtarı (`:fx` ile biter). |
| `ENGINE` | Çeviri motoru: `deepl` (varsayılan) veya `claude`. |
| `ANTHROPIC_API_KEY` | Sadece `ENGINE=claude` ise zorunlu; DeepL kullanıyorsan boş bırak. |
| `CLAUDE_MODEL` | Sadece `ENGINE=claude` için model adı (varsayılan: `claude-haiku-4-5`). |
| `DEV_GUILD_ID` | **Kendi sunucunun ID'si.** Doluysa slash komutlar o sunucuda **anında** görünür; boşsa global sync yapılır ve komutlar **1 saati bulan** sürede yayılır. Günlük kullanım için doldurulması şiddetle önerilir. |
| `ALLOWED_GUILD_IDS` | Virgülle ayrılmış sunucu ID listesi. Doluysa bot, listede olmayan bir sunucuya eklenirse **kendisi o sunucudan çıkar** (DeepL kota koruması). Boşsa her sunucu serbest. |
| `DATA_DIR` | Ayar/istatistik dosyalarının tutulduğu klasör (varsayılan: `data`). |
| `LOG_LEVEL` | Log detay seviyesi (varsayılan: `INFO`). |

**`DEV_GUILD_ID` nasıl alınır?** Discord uygulamasında: **Kullanıcı Ayarları → Gelişmiş → Geliştirici Modu**'nu aç; sonra sunucu adına **sağ tık → Sunucu Kimliğini Kopyala**.

## 6. Yerelde çalıştırma

En kolay yol, proje klasöründe PowerShell'de:

```powershell
.\run_local.ps1
```

Script venv yoksa kurar, bağımlılıkları yükler ve botu başlatır. Manuel yapmak istersen:

```powershell
py -3 -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt -r requirements-dev.txt
.venv\Scripts\python bot.py
```

Bot açıldığında logda davet linki ve "logged in as ..." satırını görürsün.

## 7. Botu sunucuya davet etme

Davet linki:

```
https://discord.com/oauth2/authorize?client_id=1552710974631583825&scope=bot+applications.commands&permissions=274877992000
```

- Bu link **Administrator izni VERMEZ**. İzin seti yalnızca şunları kapsar: **View Channels, Send Messages, Send Messages in Threads, Read Message History, Add Reactions, Embed Links**.
- Botu sunucuya ekleyen kişide **Manage Server** izni olmalı; admin komutları Manage Server izniyle korunur.

## 8. Sunucuda ilk kurulum

1. Otomatik bayrak istediğin kanala git ve `/autoflag on` yaz (kanal seçmezsen komutu yazdığın kanal için açılır).
2. Bayrak listesi sabittir ve kurulum gerektirmez: her otomatik bayraklı mesaja 🌐 + şu 14 bayrak aynı sırayla eklenir — 🇬🇧 🇹🇷 🇸🇦 🇷🇺 🇪🇸 🇧🇷 🇩🇪 🇫🇷 🇻🇳 🇮🇩 🇨🇳 🇰🇷 🇵🇭 🇯🇵. `/settings show` ile tüm ayarları (minimum uzunluk, 🌐 vb.) gözden geçir.

## 9. Komutlar

### Üye komutları

- `/translate text to` — yazdığın metni seçtiğin dile çevirir (cevap ephemeral'dır, sadece sen görürsün).
- `/mylang [dil]` — kişisel dilini ayarlar veya **değiştirir**; 🌐 menüsündeki 25 yaygın dilin dışındakiler dahil TÜM dilleri aranabilir autocomplete ile buradan seçersin. Parametresiz çağırırsan mevcut dilini gösterir. Parametresiz `/mylang` menüsünde dili seçtiysen "Reset my language" (🚫) düğmesi görünür; basınca dil silinir ve 🌐'ye tıklayınca dil seçim menüsü yeniden çıkar.
- `/help` — kısa komut rehberini gösterir.
- **Bayrağa tıklama** — mesajı o bayrağın diline çevirip altına reply olarak yazar.
- **🌐 tepkisi** — Dilin kayıtlıysa mesajı o dile çevirip orijinal mesajın altına herkese açık reply olarak yazar (DM asla gönderilmez). Dilin kayıtlı değilse bot, mesajın altında en yaygın 25 dilden oluşan tıklanabilir bir dil menüsü açar: bir dil seçmen yeterli — seçim kalıcı olarak hatırlanır ve mesaj anında o dile çevrilip altına public reply olarak gelir (sıfır kurulum, `/mylang` yazmaya gerek yok).
- **Sağ tık → Apps → "Translate to my language"** — mesajı kişisel diline çevirir, sonuç sadece sana görünür.

### Admin komutları (Manage Server izni gerekir)

- `/autoflag on [kanal]` — seçilen kanalda (yoksa komutun yazıldığı kanalda) otomatik bayrak eklemeyi açar.
- `/autoflag off [kanal]` — kanalda otomatik bayrak eklemeyi kapatır.
- `/autoflag list` — otomatik bayrağın açık olduğu kanalları listeler.
- `/settings show` — sunucunun tüm ayarlarını tek bir ephemeral mesajda gösterir.
- `/settings delete_after` — çeviri yanıtlarının kaç saniye sonra silineceğini ayarlar (0 = asla silinmez).
- `/settings min_chars` — bundan kısa mesajlara bayrak eklenmez (1–50 karakter).
- `/settings globe` — 🌐 (kişisel dil) tepkisini açar veya kapatır.
- `/settings skip_source` — kaynak dil tahmin edilip aynı dile giden bayrakları atlar (İngilizce mesaja 🇬🇧 eklenmez).
- `/settings max_lag` — bu kadar saniyeden eski mesajlara bayrak dizilmez (10–300 sn; varsayılan 45).
- `/stats` — en çok algılanan dilleri, en çok tıklanan bayrakları, toplam çeviri/karakter sayısını ve DeepL kota kullanımını gösterir.

## 10. Evdeki laptopa kurulum (7/24 servis)

Bot, evdeki eski Windows laptopunda **NSSM ile Windows servisi** olarak 7/24 çalışır: açılışta kullanıcı girişi olmadan kendiliğinden kalkar, çökerse 5 saniye sonra yeniden başlar.

1. Laptopta **Git** ve **Python 3.11+** kur (Python kurulumunda "Add python.exe to PATH" işaretli olmalı).
2. GitHub'daki **public** repoyu `git clone <repo-url>` ile klonla ve klasöre gir (repo herkese açık; clone için erişim izni gerekmez, `.env`/`data/`/`logs/` repoda bulunmaz).
3. `deploy\windows\install.ps1` dosyasını **YÖNETİCİ PowerShell**'de çalıştır. Script `.env` yoksa üretir ve `DISCORD_TOKEN`, `DEEPL_API_KEY`, `DEV_GUILD_ID` değerlerini senden sorar (geliştirme makinesindeki `.env`den kopyala-yapıştır); ardından venv'i kurar, NSSM'i indirir ve `AoEMTranslator` adlı servisi oluşturup başlatır, güç ayarlarını da (laptop uyumasın) düzenler.
4. Servis bilgisayarın her açılışında kendiliğinden kalkar; elle kontrol için `nssm status AoEMTranslator` (`SERVICE_RUNNING` beklenir).
5. Güncelleme: geliştirme makinesinde commit + push yaptıktan sonra laptopta `deploy\windows\update.ps1` çalıştır (git pull + pip install + servis yeniden başlatma). Hızlı duruma bakış: `deploy\windows\status.ps1`.
6. Loglar: `logs\bot.log`.
7. **ÖNEMLİ:** Servis çalışırken **başka bir kopyayı** (örn. geliştirme makinesinde) çalıştırma — iki kopya her mesaja çift bayrak ve çift çeviri atar. Yerelde test gerekirse **önce laptopta `nssm stop AoEMTranslator`**, iş bitince `nssm start AoEMTranslator`.

## 11. Sorun giderme

- **Bayraklar geliyor ama tıklayınca çeviri gelmiyor:** Developer Portal'da **Message Content Intent** kapalı demektir; aç ve botu yeniden başlat.
- **Slash komutlar görünmüyor:** `.env`de `DEV_GUILD_ID` boşsa komutlar global olarak sync edilir ve Discord'da **1 saati bulan** sürede yayılır; `DEV_GUILD_ID`yi doldurup botu yeniden başlat, komutlar anında çıkar.
- **Botu bir sunucuya ben ekleyemedim / admin komutları bana görünmüyor** → Bot eklemek için o sunucuda 'Sunucuyu Yönet' izni şarttır; iznin yoksa botu ancak o sunucunun yöneticisi ekleyebilir (davet linkini ona verin). Yönetici sizseniz ama komutlar görünmüyorsa: Sunucu Ayarları → Entegrasyonlar → AoEM Translator üzerinden /autoflag, /settings, /stats komutlarını belirli rol veya kullanıcılara açabilirsiniz — 'Sunucuyu Yönet' izni olmadan da bu şekilde kullanılabilir.
- **Bot bir kanalda mesaj göndermiyor / bayrak eklemiyor (kanal kilitliyse)** → Kanal Ayarları → İzinler → 'AoEM Translator' rolünü ekleyip View Channel, Send Messages, Add Reactions, Read Message History, Embed Links izinlerini açıkça ✅ yapın. Bota Administrator vermek gerekmez; kanal bazlı izin yeterlidir.
- **"Monthly translation quota exceeded" uyarısı:** Aylık DeepL kotası (500.000 karakter) bitmiştir; `/stats` ile tüketimi görüp DeepL dashboard üzerinden hesabını kontrol et.
