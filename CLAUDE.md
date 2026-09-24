# CLAUDE.md — AoEM Translator

> Bu dosya Türkçedir; gelecek Claude Code oturumları içindir. Her şeyin kaynağı `SPEC.md`dir — çelişki olursa SPEC kazanır; kullanıcının sonraki açık istekleri SPEC'i geçersiz kılar (repo artık **public**, varsayılan bayrak sayısı 14). Kullanıcıya görünen bot metinleri **İngilizce**, README ve CLAUDE.md **Türkçe**, kod/yorumlar/commit mesajları **İngilizce**dir.

## Proje özeti

AoEM Translator, Age of Empires Mobile (AoEM) Discord sunucusu için bir çeviri botudur. Seçili kanallardaki mesajlara otomatik bayrak tepkileri ekler; bir bayrağa tıklandığında mesajı (kaynak dili langdetect ile tahmin ederek) o dile çevirip yanıt olarak yazar. 🌐 tepkisi kişisel dile çeviriyi orijinal mesajın altına herkese açık reply olarak verir (🌐 için asla DM gönderilmez); `/mylang` ve sağ tık menüsü de kişisel dile çeviri sunar; tüm sunucu ayarları admin slash komutlarıyla yönetilir. Çeviri motoru `Engine` protokolü ile soyutlanmıştır (varsayılan DeepL API Free, opsiyonel Claude); bot, kullanıcının evdeki Windows laptopunda NSSM ile Windows servisi olarak 7/24 çalışır.

## Dosya haritası

- `bot.py` — giriş noktası: intents (`message_content = True`), cog yükleme, `setup_hook`'ta komut sync, `--selftest`, kapanışta temizlik.
- `translatebot/settings.py` — `.env` okuma (dataclass) ve doğrulama; eksik zorunlu değerde anlaşılır hata, token asla yazdırılmaz.
- `translatebot/flags.py` — bayrak emoji ↔ ülke/dil kodu, regional indicator parse, `LANG_NAMES`/`LANG_NAMES_EN`, `FlagResolver` (motor desteğine göre yedek/devre dışı bırakma).
- `translatebot/filters.py` — bir mesaja otomatik bayrak eklenir mi? (saf fonksiyon: mention/emoji/URL temizliği, `min_chars`, harf varlığı, `!`-prefix reddi).
- `translatebot/detect.py` — langdetect ile kaynak dil tahmini (`DetectorFactory.seed = 0`).
- `translatebot/dedupe.py` — `(message_id, target)` TTL önbelleği (3600 sn, en fazla 5000 kayıt).
- `translatebot/formatting.py` — yanıt formatı (`🇹🇷 **Türkçe** · PT → TR`) ve 2000 karakter parçalama.
- `translatebot/store.py` — `data/store.json`: sunucu ayarları, kullanıcı dilleri, istatistik; atomik yazım.
- `translatebot/reactions.py` — kanal başına sıralı tepki ekleme kuyruğu (rate limit dostu).
- `translatebot/engines/` — `__init__.py` (`build_engine(settings)`), `base.py` (`Engine` protokolü, `TranslationResult`), `deepl_engine.py`, `claude_engine.py` (opsiyonel, lazy import).
- `translatebot/cogs/translate.py` — `on_message` (otomatik bayrak), `on_raw_reaction_add`, `/translate`, `/mylang`, `/help`, context menu.
- `translatebot/cogs/admin.py` — `/autoflag`, `/flags`, `/settings`, `/stats` grupları.
- `tests/` — pytest birim testleri (flags, filters, dedupe, formatting, store); discord'a bağlanmaz, saf modülleri test eder.
- `deploy/windows/` — `install.ps1` (tek seferlik kurulum: venv + .env + NSSM servisi + güç ayarları), `update.ps1` (git pull + pip + restart), `status.ps1`, `uninstall.ps1`.
- `data/` — `store.json` (git'e girmez).
- `logs/` — `bot.log` (git'e girmez).
- `SPEC.md` — tam teknik şartname.

## Komutlar

```powershell
pytest -q                        # tüm birim testler; yeşil olmadan iş bitmiş sayılmaz
python bot.py --selftest         # Discord'a bağlanmadan yapılandırma + komut + bayrak tablosu kontrolü (exit 0 beklenir)
python bot.py                    # botu ön planda çalıştır (venv'de: .venv\Scripts\python bot.py)
deploy\windows\update.ps1        # evdeki laptopta: git pull + pip install + NSSM servis restart
```

## Tasarım kararları

- **Kanal başına tepki kuyruğu + max_lag:** Discord tepki eklemeyi kanal başına ~0,25 sn'de 1 ile sınırlar; her kanal için lazy bir `asyncio.Queue` + worker görevi emoji'leri **~0,3 sn arayla** ekler. Kuyrukta `max_lag` (varsayılan **45 sn**) süreden fazla beklemiş mesaj **atlanır** — bot dakikalar önceki mesajlara bayrak dizmez (`stats.skipped_stale`).
- **Dedupe TTL önbelleği:** Anahtar `(message_id, target)`; aynı mesaj aynı dile **1 saatte bir** çevrilir, sonraki tıklamalar sessizce yoksayılır. 🌐 (kişisel dil) yolunda anahtar kullanıcıyı da içerir.
- **🌐 her zaman herkese açık:** 🌐 (kişisel dil) çevirisi orijinal mesajın altına public reply olarak yazılır; 🌐 için hiçbir koşulda DM gönderilmez.
- **Motor soyutlaması:** `Engine` protokolü + `TranslationResult`; `build_engine(settings)` motoru seçer. **DeepL varsayılan**; **Claude opsiyonel** ve `anthropic` paketi **lazy import** edilir (requirements'a yazılmaz, sadece `ENGINE=claude` ise gerekir). Motor hataları botu asla düşürmez; kota bittiğinde kullanıcıya kısa İngilizce uyarı döner.
- **DEV_GUILD_ID sync davranışı:** Set ise `setup_hook`'ta **yalnızca o guild'e** sync yapılır (`copy_global_to` + `sync(guild=...)`) — komutlar anında görünür — ve **global sync YAPILMAZ** (çift komut olmasın). Boşsa global sync yapılır; yayılım **1 saati kadar** sürebilir. Sync asla `on_ready`'de yapılmaz (yeniden bağlanmalarda tekrar eder, rate limit yer).
- **ALLOWED_GUILD_IDS:** Doluysa `on_guild_join`'da ve başlangıçta `bot.guilds` üzerinde kontrol edilir; listede olmayan sunucudan **bot kendisi çıkar** (`guild.leave()` + WARNING) — davet linki dolaşsa da DeepL kotası yabancılar tüketemez. Boşsa her sunucu serbest.
- **Depolama:** Her şey `data/store.json`'da; yazım **atomiktir** (geçici dosyaya yaz → `os.replace`). Değişiklikte `dirty` işaretlenir, arka plan görevi 20 sn'de bir ve `bot.close()` içinde diske yazar. Bozuk dosyada `.bak` alınıp boş yapıyla başlanır.
- **Varsayılan bayrak listesi (14):** 🇬🇧 🇹🇷 🇸🇦 🇷🇺 🇪🇸 🇧🇷 🇩🇪 🇫🇷 🇻🇳 🇮🇩 🇨🇳 🇰🇷 🇵🇭 🇯🇵 — SPEC 10 bayrak derdi; kullanıcı Çince (🇨🇳), Korece (🇰🇷), Tagalogca (🇵🇭) ve Japonca (🇯🇵) bayraklarını ekletti. `/flags reset` listeyi bu 14 bayrağa döndürür.

## Kurallar

- **Sırlar asla commit edilmez:** `.env`, `data/`, `logs/` git'e girmez (`.gitignore` kapsar); commit öncesi `git status` ile doğrula, şüphede `git diff --cached` içine bak. Repo GitHub'da **public**tir; repoya giren bir sır herkese görünür ve kısa sürede kötüye kullanılır.
- **Token/API key hiçbir dosyaya veya log satırına yazılmaz** — hata mesajlarında bile değer gösterilmez.
- **Kullanıcıya görünen bot metinleri İngilizce** (sunucu uluslararası); **README.md ve CLAUDE.md Türkçe**; kod, yorumlar ve commit mesajları İngilizce.
- Her event handler `try/except Exception` ile sarılır; hiçbir istisna botu düşürmez.
- Bir bütün olarak iki kopya çalıştırmak yasaktır: laptoptaki servis ayaktayken geliştirme makinesinde ikinci kopya açmak çift bayrak/çift çeviri üretir; önce `nssm stop AoEMTranslator`.
- **Paralel ajanlar (kalıcı kullanıcı tercihi):** Birbirinden bağımsız işler (örn. üç cog dosyası, `bot.py`, gereksinim dosyaları) tek seferde paralel ajanlara yaptırılır, sırayla değil; kullanıcı bunu bundan sonra her zaman uygulanacak kalıcı bir ayar olarak istedi.
