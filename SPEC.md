# AoEM Translator — Discord Çeviri Botu Teknik Şartnamesi

> Bu dosya Claude Code için yazılmıştır. Buradaki her şeyi eksiksiz uygula. Sıra için en alttaki **"Çalışma sırası"** bölümüne uy. Belirsiz bir şey varsa kullanıcıya sor; kararları kendi başına değiştirme.

---

## 0. Özet

Uluslararası bir Age of Empires Mobile (AoEM) Discord sunucusu için çeviri botu:

- Seçili kanallardaki **her mesajın altına otomatik bayrak tepkileri** ekler (varsayılan 10 dil + 🌐).
- Biri bayrağa tıklayınca bot mesajı **o bayrağın diline** çevirir ve yanıt (reply) olarak yazar. Kaynak dil otomatik algılanır → **her dilden her dile** çalışır (Portekizce mesaj + 🇨🇳 = Çince).
- Otomatik eklenmemiş bir bayrağı kullanıcı kendisi bassa da çevirir.
- 🌐 tepkisi ve sağ tık menüsü ile **kişisel dile** çeviri (`/mylang`).
- `/ign` ile üyeler **oyun içi nicklerini** kaydeder; bot sunucu takma adını `OyunNick | Ad` yapar.
- Adminler her şeyi slash komutlarıyla ayarlar; kod değişikliği gerekmez.
- Çeviri motoru **DeepL API Free** (500.000 karakter/ay). Motor soyutlanmış; isteğe bağlı Claude API motoru.
- Kullanıcının evdeki **eski Windows laptopunda** (7/24 açık) **NSSM ile Windows servisi** olarak çalışır; açılışta kendi kalkar, çökerse yeniden başlar. (Oracle/VPS planından vazgeçildi.)
- Geliştirme Alienware laptopta, kod GitHub'da **private** repoda; eve giden laptop `git pull` ile güncellenir. **Sırlar (.env) asla commit edilmez.**

Uygulama bilgileri (kullanıcı verdi):
- Application ID / Client ID: `1552710974631583825`
- Bot adı: `AoEM Translator`
- Bot token'ı ve DeepL key'i klasördeki `.env` dosyasında (`DISCORD_TOKEN`, `DEEPL_API_KEY`) **zaten dolu**. `.gitignore` ve `.env.example` da hazır. **Token'ı/key'i hiçbir dosyaya, log'a, commit'e, README'ye yazma.** `.env` yoksa kullanıcıdan iste.

---

## 1. Teknoloji ve proje yapısı

- Python **3.11+** (geliştirme ve çalışma ortamı Windows; kod platform bağımsız olsun, yollar `pathlib`).
- `discord.py>=2.4,<3` (app_commands / slash komutları), `deepl>=1.18`, `python-dotenv`, `langdetect`, test için `pytest`. `anthropic` paketi **opsiyonel** (sadece `ENGINE=claude` ise lazım; `requirements.txt`'e koyma, lazy import et).
- Tüm kullanıcıya görünen bot metinleri **İngilizce** (sunucu uluslararası). README ve CLAUDE.md **Türkçe**. Kod, yorumlar ve commit mesajları İngilizce.

```
discordtranslatebot/
├── bot.py                      # giriş noktası, intents, cog yükleme, komut sync, --selftest
├── translatebot/
│   ├── __init__.py
│   ├── settings.py             # .env okuma (dataclass), doğrulama
│   ├── flags.py                # bayrak emoji <-> dil kodu, regional indicator parse, dil adları
│   ├── filters.py              # bir mesaja otomatik bayrak eklenir mi? (saf fonksiyon)
│   ├── detect.py               # langdetect ile kaynak dil tahmini (opsiyonel özellik)
│   ├── dedupe.py               # (message_id, target) TTL önbelleği
│   ├── formatting.py           # yanıt formatı, 2000 karakter parçalama
│   ├── store.py                # data/store.json — sunucu ayarları, kullanıcı dilleri, IGN, istatistik
│   ├── reactions.py            # kanal başına sıralı tepki ekleme kuyruğu (rate limit dostu)
│   ├── engines/
│   │   ├── __init__.py         # build_engine(settings)
│   │   ├── base.py             # Engine protokolü, TranslationResult
│   │   ├── deepl_engine.py
│   │   └── claude_engine.py    # opsiyonel
│   └── cogs/
│       ├── __init__.py
│       ├── translate.py        # on_message (otomatik bayrak), on_raw_reaction_add, /translate, /mylang, /help, context menu
│       ├── admin.py            # /autoflag, /flags, /settings, /stats
│       └── ign.py              # /ign set|remove|show|setfor
├── tests/
│   ├── test_flags.py
│   ├── test_filters.py
│   ├── test_dedupe.py
│   ├── test_formatting.py
│   └── test_store.py
├── deploy/
│   └── windows/
│       ├── install.ps1         # evdeki laptopta tek seferlik kurulum (venv, .env, NSSM servisi, güç ayarları)
│       ├── update.ps1          # git pull + pip + servisi yeniden başlat
│       ├── status.ps1          # servis durumu + son loglar
│       └── uninstall.ps1       # servisi kaldır
├── data/                       # store.json (git'e girmez)
├── logs/                       # bot.log (git'e girmez)
├── .env                        # sırlar (git'e girmez) — DISCORD_TOKEN zaten dolu
├── .env.example
├── .gitignore
├── requirements.txt
├── requirements-dev.txt        # pytest
├── run_local.ps1               # Windows'ta venv kur + botu çalıştır
├── README.md                   # Türkçe kurulum/kullanım
├── CLAUDE.md                   # gelecek Claude Code oturumları için proje notları
└── SPEC.md                     # bu dosya
```

---

## 2. Ortam değişkenleri (`.env`)

```
DISCORD_TOKEN=            # zorunlu (dosyada zaten var)
DEEPL_API_KEY=            # zorunlu (ENGINE=deepl iken); Free key ":fx" ile biter
ENGINE=deepl              # deepl | claude
ANTHROPIC_API_KEY=        # sadece ENGINE=claude
CLAUDE_MODEL=claude-haiku-4-5
DEV_GUILD_ID=             # kullanıcının sunucu ID'si → slash komutlar anında görünür (bkz. 4.10)
ALLOWED_GUILD_IDS=        # virgülle ayrılmış; boşsa her sunucu serbest. Doluysa listede olmayan sunucuya eklenince bot o sunucudan çıkar (kota koruması)
DATA_DIR=data
LOG_LEVEL=INFO
```

`.env.example` aynı anahtarları boş değerlerle içerir. `settings.py` bunları okur, eksik zorunlu değerde **anlaşılır Türkçe/İngilizce hata mesajıyla** çıkar (token'ın kendisini asla yazdırma).

---

## 3. Discord tarafı gereksinimler

**Intents:** `discord.Intents.default()` + `intents.message_content = True`. Message Content **privileged intent**; Developer Portal → Bot → Privileged Gateway Intents'te açık olmalı (kullanıcı açtı). Tepki verilen mesajın içeriğini okumak için şart. Tepki eklemek için gerekmez ama çevirmek için gerekir.

**Bot izinleri (davet linki):** Administrator **verilmez**. Gerekenler: View Channels, Send Messages, Send Messages in Threads, Read Message History, Add Reactions, Embed Links, Manage Nicknames (sadece `/ign` için). Toplam permissions integer: **`275012209728`**. Scope: `bot applications.commands`.

Davet linki (README'ye de yaz):
```
https://discord.com/oauth2/authorize?client_id=1552710974631583825&scope=bot+applications.commands&permissions=275012209728
```
Bot `on_ready`'de aynı linki `discord.utils.oauth_url(bot.user.id, permissions=discord.Permissions(275012209728), scopes=("bot", "applications.commands"))` ile loglasın.

**Rol sırası:** `/ign`'in çalışması için bot rolü, takma adı değiştirilecek üyelerin rollerinin **üstünde** olmalı. Sunucu sahibinin takma adı API ile değiştirilemez (Discord kısıtı) — bot bunu nazikçe söyler.

**Kullanıcı tarafı:** Botu sunucuya ekleyen kişide **Manage Server** izni olmalı. Admin komutları `default_permissions(manage_guild=True)` ile korunur.

---

## 4. Özellikler — ayrıntılı davranış

### 4.1 Bayrak ↔ dil eşlemesi (`flags.py`)

- Bayrak emojileri iki **regional indicator** karakteridir (U+1F1E6–U+1F1FF). `emoji_to_country("🇹🇷") -> "TR"`, `country_to_emoji("TR") -> "🇹🇷"`. Başka her şey (custom emoji, 🏴 tag dizileri, tek karakter) → `None`.
- `COUNTRY_TO_LANG: dict[str, str]` — ülke kodu → DeepL hedef kodu. En az şu tablo (eksiksiz yaz, genişletebilirsin):

| Ülke kodları | Hedef kod |
|---|---|
| GB, AU, NZ, IE, ZA, NG, SG | EN-GB |
| US, CA | EN-US |
| TR | TR |
| DE, AT, CH, LI | DE |
| FR, BE, LU, MC, SN, CI | FR |
| ES | ES |
| MX, AR, CO, CL, PE, VE, EC, UY, PY, BO, CU, DO, GT, HN, SV, NI, CR, PA, PR | ES-419 (yedek: ES) |
| PT, AO, MZ | PT-PT |
| BR | PT-BR |
| IT, SM, VA | IT |
| NL | NL |
| PL | PL |
| RU, BY | RU |
| UA | UK |
| SA, AE, EG, IQ, JO, KW, QA, BH, OM, YE, SY, LB, LY, SD, PS, MA, DZ, TN | AR |
| IR, AF | FA |
| IL | HE |
| CN | ZH-HANS (yedek: ZH) |
| TW, HK, MO | ZH-HANT (yedek: ZH) |
| JP | JA |
| KR, KP | KO |
| VN | VI |
| TH | TH |
| ID | ID |
| MY | MS |
| PH | TL |
| IN | HI |
| PK | UR |
| BD | BN |
| GR, CY | EL |
| SE | SV |
| NO | NB |
| DK | DA |
| FI | FI |
| IS | IS |
| EE | ET |
| LV | LV |
| LT | LT |
| CZ | CS |
| SK | SK |
| HU | HU |
| RO, MD | RO |
| BG | BG |
| RS, ME | SR |
| HR | HR |
| SI | SL |
| BA | BS |
| MK | MK |
| AL, XK | SQ |
| GE | KA |
| AM | HY |
| AZ | AZ |
| KZ | KK |
| UZ | UZ |
| MN | MN |
| KH | KM |
| LA | LO |
| MM | MY |
| ET | AM |
| KE, TZ | SW |

- `LANG_NAMES: dict[str, str]` — kodun **ana dilindeki adı** (EN "English", TR "Türkçe", AR "العربية", RU "Русский", ES "Español", PT "Português", DE "Deutsch", FR "Français", VI "Tiếng Việt", ID "Bahasa Indonesia", ZH-HANS "简体中文", ZH-HANT "繁體中文", JA "日本語", KO "한국어", IT "Italiano", NL "Nederlands", PL "Polski", UK "Українська", EL "Ελληνικά", SV "Svenska", NB "Norsk", DA "Dansk", FI "Suomi", CS "Čeština", SK "Slovenčina", HU "Magyar", RO "Română", BG "Български", HE "עברית", TH "ไทย", FA "فارسی", HI "हिन्दी", MS "Bahasa Melayu", …). Ayrıca İngilizce adları da tut (`LANG_NAMES_EN`) — autocomplete'te ikisiyle de aransın.
- `base_code("PT-BR") -> "PT"`, `base_code("ES-419") -> "ES"`, `base_code("ZH-HANT") -> "ZH"`.
- `preferred_flag(code)` — bir dil kodu için gösterimde kullanılacak bayrak (EN→🇬🇧, ES→🇪🇸, PT→🇧🇷, ZH→🇨🇳, AR→🇸🇦 …).
- `parse_flags(text) -> list[str]` — bir metindeki bayrak emojilerini sırayla, tekrarsız çıkarır (`/flags set` için).
- **Başlangıç doğrulaması:** bot açılırken `engine.supported_targets()` çağrılır (DeepL: `get_target_languages()`); tablo buna göre çözülür: kod destekleniyorsa kullan, değilse `base_code` destekleniyorsa onu kullan, o da yoksa bayrağı **devre dışı** bırak ve `WARNING` logla ("🇵🇭 TL not supported by engine, disabled"). Sonuç `FlagResolver` nesnesinde tutulur (`resolve(emoji) -> ResolvedLang | None`, `is_supported(emoji)`). `supported_targets()` `None` dönerse (Claude motoru) hepsi destekli sayılır.

### 4.2 Otomatik bayrak ekleme (`on_message`)

Koşullar (hepsi sağlanmalı):
- Mesaj bir sunucuda (`message.guild` var), kanal (thread ise **parent kanal**) o sunucunun `auto_channels` listesinde.
- `message.author.bot` değil, `message.webhook_id` yok, `message.type` `default` veya `reply`.
- `filters.qualifies(content, min_chars)` True: içerikten mention'lar (`<@…>`, `<#…>`, `<@&…>`), custom emoji (`<a?:name:id>`), URL'ler ve boşluklar temizlenince kalan metin ≥ `min_chars` (varsayılan 5) ve en az bir harf (`str.isalpha`) içeriyor; metin `! . ? $ -` ile **başlamıyor** (başka botların prefix komutları).
- Bot rolünün o kanalda `add_reactions` izni var (`channel.permissions_for(guild.me)`); yoksa 10 dakikada bir tek uyarı logla.

Eklenecek emoji listesi: `globe` açıksa önce 🌐, sonra sunucunun `flags` listesi. `skip_source` açıksa `detect.detect_lang(content)` ile kaynak dil tahmin edilir ve **aynı ana dile giden bayraklar atlanır** (İngilizce mesaja 🇬🇧 eklenmez; `zh-cn`/`zh-tw` ikisi de `ZH` sayılır). Tahmin başarısızsa hiçbir şey atlanmaz. Tahmin edilen dil istatistiğe yazılır (`stats.detected[lang] += 1`).

Varsayılan bayraklar (sırayla): `🇬🇧 🇹🇷 🇸🇦 🇷🇺 🇪🇸 🇧🇷 🇩🇪 🇫🇷 🇻🇳 🇮🇩`. Varsayılan `globe = true`.

**Kuyruk (`reactions.py`):** Discord tepki eklemeyi kanal başına yaklaşık **0,25 sn'de 1** ile sınırlar; 11 emoji ≈ 3 sn/mesaj. Bu yüzden:
- Kanal başına bir `asyncio.Queue(maxsize=200)` ve bir worker görevi (lazy oluşturulur). Öğe: `(message, emojis, enqueued_at=time.monotonic())`.
- Worker sırayla `await message.add_reaction(e)` yapar, aralarda `await asyncio.sleep(0.3)`. discord.py 429'ları zaten bekleyerek yönetir; biz sadece nazik davranıyoruz.
- Kuyruktan çıkarken `now - enqueued_at > settings.max_lag` (varsayılan 45 sn) ise mesaj **atlanır** (`stats.skipped_stale += 1`) — bot dakikalarca eski mesajlara bayrak dizmesin.
- Kuyruk doluysa en eskiyi düşür, yenisini al.
- Hatalar: `discord.NotFound` (mesaj silinmiş) → o mesajı bırak; `discord.Forbidden` → kanal başına 10 dk'da bir uyarı; `discord.HTTPException` → logla, devam et.
- `bot.close()` içinde worker'lar iptal edilir.

### 4.3 Tepkiyle çeviri (`on_raw_reaction_add`)

`on_reaction_add` **değil**, `on_raw_reaction_add` kullan (önbellekte olmayan eski mesajlar için de çalışsın).

Adımlar:
1. `payload.user_id == bot.user.id` → yoksay. `payload.guild_id is None` → yoksay. `payload.member.bot` → yoksay.
2. Emoji unicode değilse yoksay. `🌐` ise → 4.4'e git. Bayraksa `flag_resolver.resolve(emoji)`; `None` ise (bilinmeyen/desteklenmeyen) sessizce yoksay.
3. **Dedupe:** anahtar `(message_id, target_code)`; `dedupe.check_and_add(key)` False dönerse (son 1 saat içinde bu mesaj bu dile çevrildi) yoksay. TTL 3600 sn, en fazla 5000 kayıt.
4. Kanalı ve mesajı getir: `bot.get_channel(id) or await bot.fetch_channel(id)`, `await channel.fetch_message(payload.message_id)`.
5. Çevrilecek metin: `message.content`; boşsa embed'lerin `title`/`description`'ı; yine boşsa (sadece resim vb.) yoksay. Metin boş geliyorsa ve mesajda ek/embed de yoksa bir kez `WARNING: message content empty — Message Content Intent may be disabled in the Developer Portal` logla.
6. `await engine.translate(text, target)` → `TranslationResult(text, source)`. Kaynak dil hedefle aynıysa (`base_code` eşit) kısa bir not döndür: "Already in Türkçe." (delete_after 10).
7. Gönderim (`settings.mode`):
   - `reply` (varsayılan): `await message.reply(formatted, mention_author=False, allowed_mentions=discord.AllowedMentions.none(), delete_after=settings.delete_after or None)`.
   - `dm`: tıklayana DM; `discord.Forbidden` (DM kapalı) olursa `reply`'a düş.
8. İstatistik: `clicks[emoji] += 1`, `translations += 1`, `chars += len(text)`.

**Format (`formatting.py`):**
```
🇹🇷 **Türkçe** · PT → TR
<çeviri metni>
```
DM modunda ilk satıra `message.jump_url` de eklenir. Toplam 2000 karakteri aşarsa `chunk(text, 1900)` ile bölünür: ilki reply, kalanlar aynı kanala normal mesaj. Çeviri metni `@everyone`/`@here` içerse bile `AllowedMentions.none()` sayesinde ping atmaz.

**Hatalar:** DeepL kota bitti (`deepl.QuotaExceededException`) → "⚠️ Monthly translation quota exceeded." (delete_after 20) ve `ERROR` log; `deepl.TooManyRequestsException` → 2 sn bekle, 1 kez tekrar dene; diğer istisnalar → "⚠️ Translation failed, try again later." (delete_after 15) + traceback log. Motor hataları botu asla düşürmez.

### 4.4 Kişisel dil: `/mylang`, 🌐 ve sağ tık menüsü

- `/mylang [language]` — herkes kullanabilir, cevap **ephemeral**. Parametre autocomplete'li (en fazla 25 seçenek; kod, ana dil adı ve İngilizce ad ile arama: "tr", "Türkçe", "Turkish" hepsi bulur). Parametresiz çağrılırsa mevcut ayarı gösterir. Ayar kullanıcıya özeldir (sunucudan bağımsız), `store.users[user_id].lang`.
- 🌐 tepkisi: kullanıcının dili yoksa kısa yanıt (delete_after 15): "Set your language first with `/mylang`." Varsa çeviri **DM** ile gönderilir (kişisel); DM kapalıysa kanala reply, `delete_after=60`. Dedupe anahtarı `(message_id, target, user_id)` (kişisel olduğu için kullanıcı bazlı).
- **Context menu** (mesaja sağ tık → Apps → **"Translate to my language"**): ephemeral çeviri. Bu yol Message Content intent'e bile ihtiyaç duymaz; kanalı hiç kirletmez. Dili yoksa ephemeral olarak `/mylang` uyarısı.

### 4.5 `/translate text to`

Herkes için, ephemeral. `to` autocomplete'li dil. Metin ≤ 2000 karakter. Çeviri sırasında `await interaction.response.defer(ephemeral=True, thinking=True)` → sonra `followup.send`.

### 4.6 `/help`

Ephemeral, İngilizce, kısa: bayrağa tıkla → çeviri; 🌐 → kendi dilin; `/mylang`, `/translate`, `/ign set` açıklamaları. Adminler için `/autoflag`, `/flags`, `/settings`, `/stats` bir cümleyle.

### 4.7 Oyun içi nick: `/ign`

Grup: `/ign`
- `set nick:str` — kullanıcı kendi oyun içi adını kaydeder (`store.igns[guild][user] = nick`, 1–24 karakter, boşluk serbest). Sonra bot takma adı günceller: `settings.ign_format.format(ign=nick, name=base)`; `base = member.global_name or member.name` (**mevcut takma ad değil**, ki tekrar tekrar set edince iç içe geçmesin). Sonuç 32 karakteri aşarsa kırp. `await member.edit(nick=new, reason="IGN set via /ign")`.
  - Önce `guild.me.guild_permissions.manage_nicknames` kontrolü; yoksa: "Saved, but I don't have Manage Nicknames permission — ask an admin to grant it."
  - `discord.Forbidden` (rol sırası / sunucu sahibi): "Saved. I can't change your nickname (server owner or a role above mine) — set it manually: `OyunNick | Ad`".
  - Başarılıysa ephemeral onay.
- `remove` — kaydı siler, takma adı `None` yapar (aynı hata yönetimi).
- `show [user]` — kullanıcının (varsayılan kendisi) IGN'sini gösterir, ephemeral.
- `setfor user nick` — yalnızca `manage_nicknames` izni olanlar (`app_commands.checks.has_permissions(manage_nicknames=True)`), başkası adına ayarlar.
- Varsayılan format `"{ign} | {name}"`; admin `/settings ign_format` ile değiştirir (`{ign}` ve `{name}` zorunlu; doğrula).

### 4.8 Admin komutları (`admin.py`)

Tüm gruplar: `app_commands.Group(..., default_permissions=discord.Permissions(manage_guild=True), guild_only=True)`. Cevaplar ephemeral.

- `/autoflag on [channel]`, `/autoflag off [channel]` (varsayılan: komutun yazıldığı kanal; `Optional[discord.TextChannel]`), `/autoflag list`.
- `/flags show`, `/flags set flags:str` (metindeki bayrakları `parse_flags` ile al; desteklenmeyenleri reddet ve hangileri olduğunu söyle; 1–20 arası), `/flags add flags:str`, `/flags remove flags:str`, `/flags reset` (varsayılan 10'a döner).
- `/settings show` (tüm ayarları tek ephemeral mesajda), `/settings mode mode:Literal["reply","dm"]`, `/settings delete_after seconds:int` (0 = silme; 0–3600), `/settings min_chars n:int` (1–50), `/settings globe on_off:Literal["on","off"]`, `/settings skip_source on_off:Literal["on","off"]`, `/settings ign_format format:str`, `/settings max_lag seconds:int` (10–300).
- `/stats` — en çok algılanan 10 kaynak dil, en çok tıklanan 10 bayrak, toplam çeviri ve karakter, `skipped_stale`, motor kullanımı (`engine.usage()` → DeepL: "123,456 / 500,000 characters this period").

### 4.9 Depolama (`store.py`)

`DATA_DIR/store.json`, tek dosya:
```json
{
  "guilds": {"<gid>": {"auto_channels": [], "flags": ["🇬🇧", "…"], "globe": true, "mode": "reply",
                        "delete_after": 0, "min_chars": 5, "skip_source": true,
                        "ign_format": "{ign} | {name}", "max_lag": 45}},
  "users": {"<uid>": {"lang": "TR"}},
  "igns": {"<gid>": {"<uid>": "Nick"}},
  "stats": {"<gid>": {"detected": {}, "clicks": {}, "translations": 0, "chars": 0, "skipped_stale": 0}}
}
```
- `GuildSettings` bir `dataclass`; eksik alanlar varsayılanla doldurulur (ileride alan eklemek kolay olsun).
- Yazma **atomik** (geçici dosyaya yaz → `os.replace`). Değişiklikte `dirty=True`; arka plan görevi 20 sn'de bir dirty ise kaydeder; `bot.close()` içinde son kez kaydeder.
- Dosya yoksa boş yapı ile başla; bozuksa `.bak` alıp boş başla ve `ERROR` logla.

### 4.10 Slash komut senkronizasyonu

`setup_hook` içinde **bir kez**:
- `DEV_GUILD_ID` doluysa: `guild = discord.Object(id)`; `bot.tree.copy_global_to(guild=guild)`; `await bot.tree.sync(guild=guild)` → komutlar o sunucuda **anında** görünür. Global sync **yapma** (aynı sunucuda çift komut görünmesin).
- Boşsa: `await bot.tree.sync()` (global; Discord'un yayması 1 saate kadar sürebilir).
- `on_ready` içinde sync yapma (yeniden bağlanmalarda tekrar tekrar çalışır, rate limit yer).

### 4.11 İzinli sunucu listesi

`ALLOWED_GUILD_IDS` doluysa: `on_guild_join` ve başlangıçta `bot.guilds` üzerinde kontrol; listede olmayan sunucudan `await guild.leave()` + `WARNING` log. Böylece davet linki elden ele dolaşsa da DeepL kotasını yabancılar tüketemez.

### 4.12 Loglama, dayanıklılık, kapanış

- `discord.utils.setup_logging(level=LOG_LEVEL)`; kendi logger'ların `translatebot.*`.
- Her event handler'ı `try/except Exception` ile sar ve logla; **hiçbir istisna botu düşürmesin**.
- Kapanışta (`bot.close()` override): tepki kuyruğu iptal, store kaydet, sonra `super().close()`.
- Startup logunda: bağlı sunucu sayısı, aktif bayrak sayısı, devre dışı bayraklar, motor adı, davet linki. **Token veya API key asla loglanmaz.**

### 4.13 `python bot.py --selftest`

Discord'a **bağlanmadan**: ayarları yükler (token zorunlu değil), cog'ları yükler, `bot.tree.get_commands()` ile tüm komut adlarını yazdırır, bayrak tablosunun regional-indicator gidiş-dönüşünü doğrular, `DEEPL_API_KEY` varsa `supported_targets()` çağırıp kaç bayrağın aktif olduğunu yazar (yoksa bu adımı atlar), `exit 0`. Herhangi bir hata → `exit 1`.

---

## 5. Testler (`pytest`)

En az:
- `test_flags.py`: emoji↔ülke dönüşümü (🇹🇷↔TR, 🇬🇧→EN-GB, 🇧🇷→PT-BR, 🇨🇳→ZH-HANS), `base_code`, `parse_flags("hello 🇹🇷 x 🇩🇪🇹🇷") == ["🇹🇷","🇩🇪"]`, custom emoji/`🌐`/`🏴` → None, tablodaki her ülke kodunun 2 büyük harf olduğu, `FlagResolver` yedek mantığı (ES-419 desteklenmiyorsa ES; hiçbiri yoksa devre dışı).
- `test_filters.py`: kısa mesaj, sadece emoji, sadece URL, sadece mention, `!rank`, bot mesajı → False; normal cümle → True; `min_chars` sınırı.
- `test_dedupe.py`: ilk çağrı True, ikinci False, TTL geçince yine True (zamanı enjekte edilebilir yap), maxsize aşımı en eskiyi düşürür.
- `test_formatting.py`: format satırı, 2000+ karakter parçalama (kelime ortasından bölmemeye çalış), boş çeviri.
- `test_store.py`: tmp_path ile yükle/kaydet gidiş-dönüşü, varsayılanlar, eksik alan tamamlama, bozuk JSON kurtarma, IGN ve user lang set/get.

`pytest -q` **tamamı geçmeden** iş bitmiş sayılmaz.

---

## 6. Deploy — evdeki Windows laptop (7/24 açık), NSSM ile Windows servisi

Hedef makine: kullanıcının evdeki eski **Windows** laptopu; 7/24 açık ve prizde kalacak. Geliştirme Alienware'de yapılır, kod GitHub üzerinden laptopa gider (`git pull`). Bot **NSSM** (Non-Sucking Service Manager) ile gerçek bir Windows servisi olarak çalışır: açılışta kullanıcı giriş yapmadan başlar, çökerse 5 sn sonra yeniden başlar, loglar dosyaya döner. Bota **gelen** port gerekmez (sadece dışarı bağlanır) → güvenlik duvarı/port yönlendirme yok.

### `deploy/windows/install.ps1` — laptopta **yönetici PowerShell**'de bir kez çalıştırılır

Script proje kökünü `$PSScriptRoot\..\..` kabul eder ve şu adımları sırayla yapar (her adımı ekrana yazar, hata olursa anlaşılır mesajla durur):
1. **Ön koşullar:** `git`, Python 3.11+ (`py -3 --version` veya `python --version`), `winget`. Eksikse ne kurulacağını söyle ve dur (Python için python.org, **"Add python.exe to PATH"** işaretli).
2. **`.env`:** yoksa `.env.example`'dan üret; `DISCORD_TOKEN`, `DEEPL_API_KEY`, `DEV_GUILD_ID` değerlerini `Read-Host` ile iste (kullanıcı Alienware'deki `.env`'den kopyalayıp yapıştıracak). Sonra `icacls .env /inheritance:r /grant:r "$env:USERNAME:F" /grant:r "SYSTEM:F"` ile sadece o kullanıcı ve SYSTEM okuyabilsin.
3. **venv:** `py -3 -m venv .venv` (varsa atla), `.venv\Scripts\python -m pip install -U pip`, `... -m pip install -r requirements.txt`.
4. **Selftest:** `.venv\Scripts\python bot.py --selftest`; başarısızsa dur.
5. **NSSM:** `Get-Command nssm` yoksa `winget install --id NSSM.NSSM -e --accept-source-agreements --accept-package-agreements`; kurulumdan sonra PATH yenilenmemişse `nssm.exe`'yi `%LOCALAPPDATA%\Microsoft\WinGet\Packages` altında ara ve tam yoluyla kullan.
6. **Servis:** varsa önce `nssm stop AoEMTranslator` + `nssm remove AoEMTranslator confirm`. Sonra:
   ```
   nssm install AoEMTranslator "<proje>\.venv\Scripts\python.exe" "bot.py"
   nssm set AoEMTranslator AppDirectory "<proje>"
   nssm set AoEMTranslator DisplayName "AoEM Translator Discord Bot"
   nssm set AoEMTranslator Description "Discord translation bot (flag reactions, DeepL)"
   nssm set AoEMTranslator Start SERVICE_AUTO_START
   nssm set AoEMTranslator AppExit Default Restart
   nssm set AoEMTranslator AppRestartDelay 5000
   nssm set AoEMTranslator AppStdout "<proje>\logs\bot.log"
   nssm set AoEMTranslator AppStderr "<proje>\logs\bot.log"
   nssm set AoEMTranslator AppRotateFiles 1
   nssm set AoEMTranslator AppRotateOnline 1
   nssm set AoEMTranslator AppRotateBytes 5242880
   nssm set AoEMTranslator AppEnvironmentExtra PYTHONUNBUFFERED=1 PYTHONIOENCODING=utf-8
   nssm start AoEMTranslator
   ```
   `logs\` klasörünü önceden oluştur. Servis **LocalSystem** olarak çalışır; `.env` ve `data\` proje klasöründe olduğu için erişim sorunu yok.
7. **Güç ayarları** (laptop uyumasın, kapak kapanınca kapanmasın):
   ```
   powercfg /change standby-timeout-ac 0
   powercfg /change hibernate-timeout-ac 0
   powercfg /change monitor-timeout-ac 10
   powercfg /setacvalueindex SCHEME_CURRENT SUB_BUTTONS LIDACTION 0
   powercfg /setactive SCHEME_CURRENT
   ```
   Kullanıcıya ayrıca yazdır: laptop prizde kalsın, mümkünse Ethernet; Wi-Fi ise adaptörün "güç tasarrufu için kapat" seçeneği kapalı olsun; Windows Update etkin saatlerini ayarlasın.
8. **Sonuç:** `nssm status AoEMTranslator` (beklenen `SERVICE_RUNNING`) ve `Get-Content logs\bot.log -Tail 20`; logda davet linki ve "logged in as" satırı görünmeli.

### Diğer scriptler
- `deploy/windows/update.ps1` — `git pull --ff-only` → `.venv\Scripts\python -m pip install -r requirements.txt` → `nssm restart AoEMTranslator` → 3 sn bekle → `nssm status` + son 15 log satırı.
- `deploy/windows/status.ps1` — `nssm status` + son 30 log satırı (hızlı bakış).
- `deploy/windows/uninstall.ps1` — `nssm stop` + `nssm remove AoEMTranslator confirm`.

### Notlar
- Bot Windows'ta çalışacağı için kodda platforma özel şey olmasın; discord.py Windows'un varsayılan event loop'uyla sorunsuz çalışır; dosya yolları `pathlib`.
- Log dosyası UTF-8 (`PYTHONIOENCODING=utf-8`) — Türkçe ve bayrak karakterleri bozulmasın. `logging` çıktısı stdout'a gitsin, NSSM dosyaya yazar.
- **Aynı anda iki kopya çalışmasın:** laptoptaki servis ayağa kalkınca kullanıcıya Alienware'deki yerel botu kapatmasını hatırlat; iki kopya her mesaja çift bayrak ve çift çeviri atar. Yerelde test gerekirse önce laptopta `nssm stop AoEMTranslator`.

---

## 7. Git ve GitHub

- **İlk iş** `.gitignore` (git init'ten önce):
  ```
  .env
  .env.*
  !.env.example
  data/
  venv/
  .venv/
  __pycache__/
  *.pyc
  .pytest_cache/
  logs/
  .claude/settings.local.json
  ```
- `git init -b main`, `git add .`, commit'ten önce `git status` ve `git check-ignore -v .env data/ logs/` ile sırların dışarıda olduğunu **doğrula**; ilk commit: `Initial commit: AoEM Translator bot`.
- GitHub: `gh --version` yoksa `winget install --id GitHub.cli -e` ve yeni terminal; `gh auth status` yoksa `gh auth login` (kullanıcı tarayıcıdan onaylar). Sonra `gh repo create discordtranslatebot --private --source=. --remote=origin --push`. `gh` kullanılamıyorsa kullanıcıya github.com'da boş **private** repo açtır, `git remote add origin …` + `git push -u origin main`.
- Sonraki her anlamlı adımda küçük, açıklayıcı commit'ler at ve push'la. **Token/API key içeren bir dosya asla stage edilmez**; şüphede `git diff --cached | findstr /i "token key"` ile bak.

---

## 8. README.md (Türkçe) içermeli

1. Ne yapar (kısa), 2. Gereksinimler (Python 3.11+, Git), 3. Discord Developer Portal ayarları (intent, Public/Private, Install Link None), 4. DeepL Free key alma, 5. `.env` doldurma, 6. Yerelde çalıştırma (`run_local.ps1`), 7. Davet linki + rol sırası notu (`/ign` için bot rolünü yukarı taşı), 8. Sunucuda ilk kurulum: `/autoflag on`, `/flags show`, `/settings show`, 9. Komut listesi (üye/admin), 10. Evdeki laptopa kurulum (Git + Python kur, repoyu klonla, `deploy\windows\install.ps1`'i yönetici olarak çalıştır), güncelleme (`update.ps1`), loglar (`logs\bot.log`), 11. Sorun giderme: bayrak geliyor ama çeviri gelmiyor → Message Content Intent; komutlar görünmüyor → DEV_GUILD_ID / 1 saat; `/ign` çalışmıyor → rol sırası; kota bitti → `/stats`.

## 9. CLAUDE.md içermeli

Proje özeti (3–4 cümle), dosya haritası, komutlar (`pytest -q`, `python bot.py --selftest`, `python bot.py`, `deploy\windows\update.ps1`), tasarım kararları (kanal başına tepki kuyruğu ve max_lag, dedupe, motor soyutlaması, DEV_GUILD_ID sync davranışı, ALLOWED_GUILD_IDS), kurallar (sırları commit etme, kullanıcıya görünen metinler İngilizce, README Türkçe).

---

## 10. discord.py tuzakları (bunlara dikkat et)

- Context menu bir Cog içinde decorator ile tanımlanamaz: `__init__`'te `self.ctx_menu = app_commands.ContextMenu(name="Translate to my language", callback=self._ctx_translate)`, `cog_load`'da `bot.tree.add_command(self.ctx_menu)`, `cog_unload`'da `bot.tree.remove_command(self.ctx_menu.name, type=self.ctx_menu.type)`. Callback imzası `(self, interaction: discord.Interaction, message: discord.Message)`.
- `app_commands.Group` bir Cog'da **sınıf niteliği** olarak tanımlanır; alt komutlar `@grup.command()` ile. Komut/parametre adları küçük harf, boşluksuz, ≤32; açıklamalar ≤100 karakter, boş olamaz.
- Interaction'a **3 saniye** içinde cevap verilmeli: çeviri gibi yavaş işlerden önce `defer`.
- `payload.emoji.name` unicode emoji için emojinin kendisidir; `payload.emoji.is_unicode_emoji()` ile kontrol et. Bayrak = 2 codepoint, `len()` 2 döner.
- `member.edit(nick=...)` → sunucu sahibi ya da bot rolünden yüksek roller için `Forbidden`.
- Autocomplete en fazla 25 `app_commands.Choice`; `current` ile filtrele; 3 sn içinde dön.
- `typing.Literal[...]` parametreleri otomatik seçenek (choice) olur.
- `deepl` ve `langdetect` senkron kütüphaneler → `asyncio.to_thread` ile çağır; event loop'u bloklama. `langdetect.DetectorFactory.seed = 0` ve `LangDetectException`'ı yakala.
- `message.reply(..., delete_after=...)` `float | None` alır; `0` verme, `None` ver.
- `discord.Intents.default()` zaten `guild_reactions` ve `guild_messages` içerir; sadece `message_content` eklenir. `members`/`presences` **gerekmez**.
- Sync'i `setup_hook`'ta bir kez yap; `on_ready` yeniden bağlanmada tekrar tetiklenir.
- Windows'ta PowerShell script çalıştırma engeli olabilir: venv'i aktive etmek yerine doğrudan `.venv\Scripts\python.exe` kullan; `py -3 -m venv .venv` ile oluştur.

---

## 11. Çalışma sırası (bu sırayla ilerle; her ana adımın sonunda kullanıcıya 2–3 satır özet ver)

1. **Ortam kontrolü:** `python --version` (3.11+ değilse python.org'dan "Add to PATH" işaretli kurdur), `git --version`, `gh --version`. Eksik olanlar için kullanıcıya net komut/link ver ve bekle.
2. **İskelet:** `.gitignore`, `.env` ve `.env.example` klasörde hazır (gerekirse `.gitignore`'a ekleme yap, silme). Mevcut `.env`'yi sadece oku; tek eksik `DEV_GUILD_ID` — kullanıcıdan iste ve `.env`'ye ekle. Sunucu ID'si için: Discord → Kullanıcı Ayarları → Gelişmiş → Geliştirici Modu aç → sunucu adına sağ tık → "Sunucu Kimliğini Kopyala".
3. **venv + testler:** `py -3 -m venv .venv`, `.venv\Scripts\python -m pip install -r requirements.txt -r requirements-dev.txt`, `pytest -q`, `python bot.py --selftest`. Geçene kadar düzelt.
4. **Git + GitHub:** ilk commit, private repo, push. Sırların dışarıda olduğunu doğrula.
5. **Yerel çalıştırma:** `.venv\Scripts\python bot.py` (kullanıcı ayrı bir terminalde açık tutar). Log'daki davet linkini ver; kullanıcı botu sunucuya ekleyip `/autoflag on`, bir mesaj, bir bayrak tıklaması, `/mylang`, 🌐, `/ign set` testlerini yapana kadar bekle; sorun varsa düzelt, commit'le.
6. **Laptop kurulumu:** `deploy/windows/*.ps1` dosyalarını yaz, README'ye laptop adımlarını ekle, commit + push. Kullanıcı evdeki laptopta Git + Python kurup repoyu klonlayacak ve `deploy\windows\install.ps1`'i yönetici olarak çalıştıracak (script token/key soracak). Servis kalkınca kullanıcıya **Alienware'deki yerel botu kapatmasını** söyle. Sonraki güncellemeler: Alienware'de commit + push → laptopta `update.ps1`.
7. **Kapanış:** README/CLAUDE.md güncel mi kontrol et, son commit + push, kullanıcıya günlük kullanım özeti (komutlar, deploy, `/stats`).

## 12. Kabul kriterleri

- `pytest -q` yeşil, `python bot.py --selftest` exit 0.
- Bot açılınca log: sunucu sayısı, aktif/devre dışı bayrak sayısı, motor, davet linki; token/key yok.
- `/autoflag on` yapılan kanalda yeni mesaja ≤ 5 sn içinde 🌐 + bayraklar gelir; kısa/emoji/komut mesajlarına gelmez.
- Portekizce bir mesaja 🇨🇳 basınca Çince reply gelir; aynı bayrağa ikinci kişi basınca **ikinci reply gelmez**.
- Otomatik listede olmayan bir bayrak (ör. 🇯🇵) basılınca da çeviri gelir.
- `/mylang Türkçe` → 🌐 tıklayınca DM'den Türkçe çeviri; sağ tık menüsü ephemeral çeviri verir.
- `/ign set Aliey` → takma ad `Aliey | <ad>` olur (rol sırası uygunsa); sahibi için nazik uyarı.
- `/settings show`, `/flags set 🇹🇷 🇬🇧 🇸🇦`, `/stats` çalışır ve `data/store.json` yeniden başlatmada korunur.
- `ALLOWED_GUILD_IDS` doluyken listede olmayan sunucuya eklenince bot çıkar.
- GitHub private repoda `.env`, `data/`, `logs/` **yok**.
- Laptopta `nssm status AoEMTranslator` → `SERVICE_RUNNING`; laptop yeniden başlayınca kullanıcı giriş yapmadan bot kendiliğinden kalkar; `update.ps1` sonrası servis ayakta.
