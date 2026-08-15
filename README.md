# IngatlanMonitor

Gmail-alapú ingatlanfigyelő: a beérkező portál-értesítőket automatikusan
feldolgozza, helyben futó LLM-mel kiértékeli és pontozza őket, a találatokat
MariaDB-be menti, és Telegramon szól, ha valóban érdekes hirdetés érkezett.

Spanyol (és belga) ingatlankereséshez készült, de a szabályrendszer szabadon
átírható: a szűrés egy Markdown fájlban leírt kritériumhalmaz alapján történik.

---

## Mit csinál

```
Gmail (címke: Hírlevelek/Ingatlan)
        │
        ├─ 30 percenként lefut egy cron a konténerben
        │
        ▼
  E-mail feldolgozás            idealista · kyero · thinkspain · fotocasa · immoweb
        │                       portálonként eltérő levélformátum
        ▼
  LLM-es adatkinyerés           Ollama (helyben futó modell)
        │                       ár, méret, kert, parkoló, város → strukturált JSON
        ▼
  Szabályalapú pontozás         RULES.md / RULES_BE.md
        │                       tengertől való távolság, reptér, ár, alapterület…
        ▼
  MariaDB ─────────────► Flask dashboard (böngésző, szűrés, kedvencek, jegyzetek)
        │
        └─ 7+ pont ──────► Telegram értesítés
```

## Fő funkciók

- **Több portál, több ország.** Portálonként külön levélfeldolgozás; új ország
  felvétele egy portállista és egy szabályfájl hozzáadása.
- **Helyben futó LLM.** A hirdetés szövegéből az Ollama nyer ki strukturált
  adatokat — nincs külső AI-szolgáltatás, a levelek nem hagyják el a gépet.
- **Szabályrendszer Markdownban.** A `RULES.md` emberi nyelven leírt kritériumok
  halmaza; ez megy be a modell promptjába, és ez alapján kap pontot a hirdetés.
- **Földrajzi számítások.** Legközelebbi reptér, tengertől mért távolság,
  legközelebbi IKEA és Lidl — a napi élet szempontjából fontos távolságok.
- **Dashboard.** Flask + gunicorn: szűrés ország/régió/ár/méret szerint,
  kedvencek, saját jegyzetek, képek, opcionális DeepL-fordítás.
- **Telegram-értesítés** csak a küszöb feletti találatokról.
- **Duplikátumszűrés**: a feldolgozott levél-ID-k állapotfájlban maradnak, egy
  hirdetés nem jön be kétszer.

## Technológia

| Réteg | Eszköz |
|---|---|
| Feldolgozás | Python 3.11, Gmail API (OAuth2) |
| AI | Ollama (helyben futó LLM) |
| Adatbázis | MariaDB (PyMySQL) |
| Webes felület | Flask + gunicorn |
| Értesítés | Telegram Bot API |
| Futtatás | Docker Compose, konténeren belüli cron |

---

## Telepítés

### Előfeltételek

- Docker és Docker Compose
- MariaDB 
- Ollama futó példány egy elérhető modellel
- Google Cloud projekt engedélyezett Gmail API-val

### 1. Kód letöltése

```bash
git clone https://github.com/tipcsy/IngatlanMonitor.git
cd IngatlanMonitor
```

### 2. Konfiguráció

```bash
cp .env.example .env
```

Töltsd ki a `.env` fájlt — minden beállítás magyarázata megtalálható. Ha valami kulcs hiányzik,
a program indulásakor hibaüzenettel leáll.

### 3. Gmail-hozzáférés

1. A Google Cloud Console-ban hozz létre egy projektet, és engedélyezd a Gmail API-t.
2. Készíts **OAuth kliens azonosítót** (asztali alkalmazás típus), és töltsd le
   a JSON-t `client_secret.json` néven.
3. Másold az `INGATLAN_DATA` könyvtárba (ezt a `.env`-ben adtad meg).
4. Első futtatáskor a program böngészőben kéri a hozzájárulást, és elmenti a
   `token.pickle` fájlt ugyanoda. Ezt követően felügyelet nélkül fut.

A Gmailben legyen egy `Hírlevelek/Ingatlan` címke, és a portálok levelei erre
érkezzenek (Gmail-szűrővel automatizálható).

### 4. Adatbázis

```bash
mysql -u root -p ingatlan < dashboard/schema.sql
```

Meglévő SQLite adatbázisból migrálni:

```bash
python migrate_sqlite_to_mariadb.py
```

### 5. Indítás

```bash
docker compose up -d
```

A dashboard ezután a `http://<szerver>:5000` címen érhető el. A figyelő
konténer 30 percenként magától lefut.

---

## Használat

Naplók:

```bash
docker compose logs -f ingatlan
```

Egyszeri ellenőrzés Telegram-értesítés nélkül (debug profil):

```bash
docker compose --profile debug run --rm simple-check      # rövid összegzés
docker compose --profile debug run --rm detailed-check    # részletes kiírás
docker compose --profile debug run --rm debug-24h         # utolsó 24 óra újrafeldolgozása
```

### Szabályrendszer módosítása

A pontozás a `RULES.md` (Spanyolország) és `RULES_BE.md` (Belgium) fájlokban
leírt kritériumok alapján történik. Ezek sima Markdown fájlok — átírásukhoz nem
kell a kódhoz nyúlni, a következő futásnál már az új szabályok érvényesek.

---

## Projektstruktúra

```
.
├── docker-compose.yml           ← 5 szolgáltatás (figyelő, dashboard, 3 debug)
├── .env.example                 ← konfigurációs minta (a valódi .env gitignore-olt)
├── gmail-watcher/               ← e-mail feldolgozás, LLM-értékelés, Telegram
│   ├── gmail_watcher.py         ← belépési pont, 30 percenként fut
│   ├── db.py                    ← MariaDB réteg
│   ├── envfile.py               ← .env betöltés külső függőség nélkül
│   └── entrypoint.sh            ← cron indítása a konténerben
├── dashboard/                   ← Flask webes felület
│   ├── app.py
│   ├── config.py
│   └── schema.sql               ← adatbázisséma
├── RULES.md / RULES_BE.md       ← a pontozás kritériumai (emberi nyelven)
└── migrate_sqlite_to_mariadb.py ← egyszeri adatmigráció
```

---

## Biztonság

- A jelszavak a `.env` fájlban vannak tárolva, ami nem kerül verziókövetésre.
- A `client_secret.json` és a `token.pickle` szintén kimarad a verziókövetésből.
- A `.env.example` a kulcsok nevét és magyarázatát tartalmazza.

## Licenc

MIT — lásd a [LICENSE](LICENSE) fájlt. Szabadon használható, módosítható és
terjeszthető, a szerzői jogi megjegyzés megtartásával.

