# Ingatlan Szűrési Szabályrendszer — Belgium

Utolsó frissítés: 2026-07-29

---

## 🌍 Ország

- **Csak Belgium**
- Nincs régiós megkötés Belgiumon belül (Flandria / Vallónia / Brüsszel régió mind elfogadható), a döntő szempont a Brüsszeltől és a repülőtértől mért távolság (lásd lent).

---

## ✅ KÖTELEZŐ FELTÉTELEK (MUST HAVE)

### 🏛️ Brüsszeltől (főváros) való távolság
- Maximum **50 km** (légvonalban) Brüsszel központjától.

### 🚶 Városközponttól / Bevásárlástól
- Városközpont: **gyalog max 10 perc** (kb. 800m-1km)
  - ⚠️ FONTOS: Ha a leírásban "5-10 perc autóval" szerepel → az NEM felel meg!
  - Keresendő kifejezések: "te voet", "à pied", "walking distance", "centrum", "centre-ville"
- Bevásárlóhely (szupermarket, piac): **max 15 perc autóval**

### 📐 Ingatlan mérete
- Minimum **100 m²** alapterület (lakható)

### 🌿 Kert / Telek
- Valódi kert vagy telek szükséges
- ⚠️ FONTOS: Terasz ≠ Kert!
  - "100 m² terras/terrasse" → NEM felel meg
  - "tuin", "jardin", "perceel", "terrain" → elfogadható
- Ha nem egyértelmű a leírásból → "kert kérdéses" státuszba kerül

### 🚗 Parkolás / Elektromos töltés
- **Kocsibeálló KÖTELEZŐ** (otthoni töltés elektromos autóhoz)
- Elfogadható: garázs ("garage"), magán parkoló, saját beálló a telken ("oprit"/"allée")
- NEM elfogadható: csak utcai parkolás
- Garázs: előny, de nem kizáró ha nincs

### ✈️ Repülőtértől való távolság
- Maximum **60 km** a Budapestről közvetlen járattal elérhető belga repülőterek valamelyikétől:
  - Brüsszel-Zaventem (BRU), Brüsszel-Charleroi (CRL)

---

## 💰 ÁR

### Hitel nélkül
- Max vételár: **170.000 €**
- + belga regisztrációs illeték (droits d'enregistrement / registratierechten), régiónként (Flandria/Vallónia/Brüsszel) eltérő mértékű — a pontos %-ot itt nem rögzítjük, ezt a felhasználónak érdemes esetenként ellenőriznie, ne tekintsük a fenti 170k-t a teljes költségnek.

### Hitellel
- Max vételár: **320.000 €**
- + regisztrációs illeték (lásd fent)
- Megjegyzés: hitel bizonytalan → mindig jelenjen meg, de külön oszlopban jelölve

---

## 🏠 INGATLAN TÍPUS

### Preferált
- **Villa / ház** (önálló vagy sorház)
- Apartman **csak akkor** ha: saját kert/patio tartozik hozzá

### Elfogadott
- Használt ingatlan ✅
- Új építésű ✅ (ha az árkategóriába esik)
- Felújítandó ✅ (jelöld meg külön)

### KIZÁRVA — Jogi státusz
- ❌ **Hosszú távú, felmondhatatlan bérleti jogviszonnyal terhelt** ingatlan (bérlő lakja, a vevő saját célra nem tudja felszabadítani) — a spanyol "ocupas" belga megfelelője
- ❌ **Haszonélvezeti jog / vruchtgebruik / usufruit** — csak a puszta tulajdon (bloot eigendom / nue-propriété) kerül eladásra, teljes birtoklási jog nélkül — a spanyol "nuda propiedad" megfelelője
- ❌ **Hosszú lejáratú földbérlet (erfpacht / emphytéose)**, ha nem egyértelműen hosszú (>50 év) és kedvező feltételű — kérdéses státuszba kerül, ha nem egyértelmű
- ❌ **Csak szezonálisan látogatható / nyaralóként** hasznosítható ingatlan
- ❌ Emeleti lakás kert nélkül (szinte biztosan nincs kertje)

---

## ⭐ PONTOZÁSI RENDSZER (1-10)

| Szempont | Súly | Pontozás |
|---|---|---|
| Főváros (Brüsszel) közelség | 20% | <20km=10, 20-35km=7, 35-50km=5 |
| Városközpont (gyalog) | 20% | <5perc=10, 5-10perc=7, >10perc=3 |
| Ár (hitel nélküli tartomány) | 20% | <130k€=10, 130-150k€=8, 150-170k€=6 |
| Ingatlan méret | 15% | >150m²=10, 120-150m²=7, 100-120m²=5 |
| Kert minősége | 15% | Nagy kert=10, kis kert=6, patio=3 |
| Parkolás/töltés | 10% | Garázs=10, beálló=7, nincs=0 |
| Repülőtér közelség | 0% | Csak kizáró (>60km → nem jelenik meg) |

**7 pont felett → Telegram értesítés!**
**5-7 pont → Megjelenik a táblázatban, de nincs push értesítés**
**5 pont alatt → Eldobva**

---

## 📧 FORRÁS PORTÁLOK

| Portál | Email feladó | Státusz |
|---|---|---|
| immoweb.be | *@immoweb.be | ✅ Aktív |

---

## 📊 OUTPUT FORMÁTUM

Minden feldolgozott ingatlanhoz:
- Cím / város
- Ár (€) + becsült illetékkel együtt
- Ingatlan m² + telek m² (ha van)
- Szobák és fürdőszobák száma (ha szerepel a hirdetésben)
- Brüsszel (főváros) távolság (km)
- Repülőtér távolság (km)
- Városközpont távolság (perc gyalog / módszer)
- Parkolás típusa
- Jogi státusz (ok / ⚠️ kérdéses / ❌ kizárt)
- Összpontszám (1-10)
- Link az ingatlanhoz
- Email érkezési dátum
