# Ingatlan Program - TrueNAS Szerver Telepítés

## Elõkészületek

### 1. Google Service Account Beállítása

Az ingatlan program szerver szintjén futatódik, ezért nem használható a Desktop OAuth (`client_secret.json`).
Szükséges: **Google Cloud Service Account** JSON kulcs.

**Lépések:**
1. Google Cloud Console: https://console.cloud.google.com/
2. Project létrehozása vagy kiválasztása
3. **APIs & Services** → **Service Accounts**
4. **Create Service Account**
   - Név: `ingatlan-watcher`
   - Engedélyek: `Editor` (vagy csak Gmail API)
5. **Create key** → **JSON** formátum
6. Letöltött fájl: `service-account-key.json`
7. Fájl másolása: `gmail-watcher/client_secret.json` (átnevezés)

### 2. Gmail API Engedélyek

Google Cloud Console-ban:
1. **APIs & Services** → **Enabled APIs & services**
2. **Enable APIs and Services**
3. Keresés: "Gmail API"
4. **Enable**

### 3. Telegram Bot Token & Chat ID

- Telegram Bot token: `TELEGRAM_TOKEN` (már van .env-ben)
- Telegram Chat ID: `TELEGRAM_CHAT_ID` (már van .env-ben)

---

## Telepítési Lépések (TrueNAS szerveren)

### 1. Szerver Mappája Létrehozása

```bash
# SSH-val TrueNAS-ra
ssh root@nas.tipcsy.hu

# Mappák létrehozása
mkdir -p /mnt/Vol003/Share/Program\ Files/IngatlanMonitor
cd /mnt/Vol003/Share/Program\ Files/IngatlanMonitor
```

### 2. Ingatlan Program Másolása

**Opció A: Git clone (ajánlott)**
```bash
# Ha git repo-ból szeretnéd másolni
git clone https://github.com/your-repo/ingatlan.git .
cd ingatlan
```

**Opció B: SCP másolás (lokális gépről)**
```bash
# Lokális gépről (pl. Windows PowerShell vagy WSL)
scp -r C:\Users\tipcs\.openclaw\workspace\sessions\ingatlan root@nas.tipcsy.hu:/mnt/Vol003/Share/Program\ Files/IngatlanMonitor/
cd /mnt/Vol003/Share/Program\ Files/IngatlanMonitor/ingatlan
```

### 3. Google Service Account Kulcs Másolása

```bash
# A letöltött service-account-key.json-t másolni kell
# Helye szerveren: /mnt/Vol003/Share/Program\ Files/IngatlanMonitor/ingatlan/gmail-watcher/

# Ha SCP-vel: szerveren már benne van az ingatlan mappában
# Ha git-ből: manuálisan kell feltölteni (biztonsági oka miatt)

# Helyes név:
mv client_secret.json.example client_secret.json
# VAGY: szerveren létrehozni a fájlt és másolni bele a JSON tartalmat
```

### 4. Docker Image Build

```bash
cd /mnt/Vol003/Share/Program\ Files/IngatlanMonitor/ingatlan/gmail-watcher

docker build -t ingatlan-watcher:latest .

# Ellenõrzés:
docker images | grep ingatlan-watcher
```

### 5. Test Futtatás (Manuális)

```bash
cd /mnt/Vol003/Share/Program\ Files/IngatlanMonitor/ingatlan

# Docker container futtatása interaktívan
docker run -it --rm \
  -v $(pwd)/gmail-watcher/.env:/app/ingatlan/.env:ro \
  -v $(pwd)/gmail-watcher/client_secret.json:/app/ingatlan/client_secret.json:ro \
  -v $(pwd)/gmail-watcher/state.json:/app/ingatlan/state.json \
  -v $(pwd)/gmail-watcher/token.pickle:/app/ingatlan/token.pickle \
  -v $(pwd)/RULES.md:/app/ingatlan/RULES.md:ro \
  ingatlan-watcher:latest

# Vagy docker-compose-val:
docker-compose run --rm ingatlan
```

### 6. Cron Job Beállítása (9:00 AM Naponta)

#### Opció A: Linux Cron

```bash
# Crontab szerkesztés
crontab -e

# Sorba beszúrni:
0 9 * * * cd /mnt/Vol003/Share/Program\ Files/IngatlanMonitor/ingatlan && docker-compose run --rm ingatlan >> /var/log/ingatlan-cron.log 2>&1
```

#### Opció B: TrueNAS Scheduled Task (Web UI)

1. **TrueNAS Web UI** → http://nas.tipcsy.hu/ui/
2. **System** → **Scheduled Tasks**
3. **Create Scheduled Task**
   - **Type**: Command
   - **Command**:
     ```
     /bin/sh -c 'cd /mnt/Vol003/Share/Program\ Files/IngatlanMonitor/ingatlan && /usr/local/bin/docker-compose run --rm ingatlan'
     ```
   - **Cron Expression**: `0 9 * * *` (9:00 AM)
   - **User**: `root`
   - **Enabled**: ✓
   - **Stdout**: `/var/log/ingatlan-cron.log`
   - **Stderr**: `/var/log/ingatlan-cron.log`

---

## Ellenõrzések és Troubleshooting

### Docker Image Jó?
```bash
docker images | grep ingatlan-watcher
```

### Container Futó?
```bash
docker ps | grep ingatlan
# vagy
docker logs ix-ingatlan
```

### State.json Feltöltve?
```bash
cat /mnt/Vol003/Share/Program\ Files/IngatlanMonitor/ingatlan/gmail-watcher/state.json
```

### Cron Log?
```bash
tail -f /var/log/ingatlan-cron.log
```

### Telegram Tesztelés?
```bash
docker run -it --rm \
  -v $(pwd)/gmail-watcher/.env:/app/ingatlan/.env:ro \
  ingatlan-watcher:latest \
  python test_telegram.py
```

---

## Biztonsági Megjegyzések

⚠️ **FONTOS:**

1. **client_secret.json**: NE commit-áld git-re! Add a `.gitignore`-hoz.
2. **.env**: NE commit-áld git-re! Tartalmazza a Telegram token-t.
3. **token.pickle**: NE commit-áld git-re! Érzékeny OAuth token.
4. **Volume jogosultságok**: Ellenõrizd, hogy az ingatlan mappának `root:root` vagy megfelelõ jogosultsága van-e.

```bash
chmod 700 /mnt/Vol003/Share/Program\ Files/IngatlanMonitor/ingatlan/gmail-watcher/.env
chmod 700 /mnt/Vol003/Share/Program\ Files/IngatlanMonitor/ingatlan/gmail-watcher/client_secret.json
```

---

## Monitoring

### Heti Log Ellenõrzés

```bash
# Utolsó 50 sor az ingatlan cron logból
tail -50 /var/log/ingatlan-cron.log

# Hibaüzenet keresése
grep -i error /var/log/ingatlan-cron.log
```

### Telegram Értesítés Teszt

Ha 7+ pontú ajánlat érkezik, Telegram üzenet küldõdik a `TELEGRAM_CHAT_ID`-be.

---

## Frissítés (jövõben)

```bash
cd /mnt/Vol003/Share/Program\ Files/IngatlanMonitor/ingatlan

# Git pull-val
git pull origin main

# Docker image rebuild
docker build -t ingatlan-watcher:latest ./gmail-watcher/

# Cron job már az új image-et fogja használni
```
