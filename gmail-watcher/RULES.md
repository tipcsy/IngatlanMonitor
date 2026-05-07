# Ingatlan Szűrési Szabályrendszer

Utolsó frissítés: 2026-03-18

---

## 🌍 Ország / Régió
- **Csak Spanyolország**
- Elfogadott régiók (reptér alapján, max 100 km):
  - Costa del Sol → **Malaga reptér** (AGP)
  - Costa Blanca → **Alicante reptér** (ALC)
  - Costa Cálida → **Murcia/Corvera reptér** (RMU)
  - Valencia környéke → **Valencia reptér** (VLC)
  - Baszkföld (Atlanti-part) → **Bilbao reptér** (BIO) ⚠️ esős éghajlat, alacsony prioritás
- **KIZÁRVA:** Szigetek (Mallorca, Kanári-szigetek, stb.)

---

## ✅ KÖTELEZŐ FELTÉTELEK (MUST HAVE)

### 🏖️ Tengertől való távolság
- Maximum **30 km** (légvonalban)
- Ha a pontos cím nem ismert → a város középpontjától számítva
- Minimum elfogadható: 20 km felett már jelöld meg "távolabb" státusszal

### 🚶 Városközponttól / Bevásárlástól
- Városközpont: **gyalog max 10 perc** (kb. 800m-1km)
  - ⚠️ FONTOS: Ha a leírásban "5-10 perc autóval" szerepel → az NEM felel meg!
  - Keresendő kifejezések: "a pie", "andando", "walking distance", "centro"
- Bevásárlóhely (szupermarket, piac): **max 15 perc autóval**

### 📐 Ingatlan mérete
- Minimum **100 m²** alapterület (lakható)

### 🌿 Kert / Telek
- Valódi kert vagy telek szükséges
- ⚠️ FONTOS: Terasz ≠ Kert! 
  - "100 m² terraza" → NEM felel meg
  - "jardín", "garden", "huerto", "parcela", "terreno" → elfogadható
- Ha nem egyértelmű a leírásból → "kert kérdéses" státuszba kerül

### 🚗 Parkolás / Elektromos töltés
- **Kocsibeálló KÖTELEZŐ** (otthoni töltés elektromos autóhoz)
- Elfogadható: garázs, magán parkoló, saját beálló a telken
- NEM elfogadható: csak utcai parkolás
- Garázs: előny, de nem kizáró ha nincs

### ✈️ Reptértől való távolság
- Maximum **100 km** a következő repterektől valamelyikétől:
  - Malaga (AGP), Alicante (ALC), Murcia-Corvera (RMU), Valencia (VLC), Bilbao (BIO)

---

## 💰 ÁR

### Hitel nélkül
- Max vételár: **170.000 €**
- + ingatlanszerzési adó (régiónként):
  - Alicante / Valencia / Murcia: ~10%
  - Andalúzia (Malaga): ~7-10%
  - Baszkföld (Bilbao): ~4-6%
- **Teljes max költség (hitel nélkül): ~190.000 €**

### Hitellel
- Max vételár: **320.000 €**
- + ingatlanszerzési adó
- **Teljes max költség (hitellel): ~355.000 €**
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
- ❌ **Ocupas** (lakásfoglalók által lakott)
- ❌ **Életjáradéki szerződés** ("nuda propiedad", "usufructo vitalicio")
- ❌ **Csak szezonálisan látogatható** ("solo meses de verano", vacation-only)
- ❌ **Csak medencés közösségi komplex** pool nélkül (pool nem fontos, de ne legyen kizárólag közösségi)
- ❌ Emeleti lakás kert nélkül (szinte biztosan nincs kertje)

---

## ⭐ PONTOZÁSI RENDSZER (1-10)

| Szempont | Súly | Pontozás |
|---|---|---|
| Tenger közelség | 20% | <10km=10, 10-20km=7, 20-30km=5 |
| Városközpont (gyalog) | 20% | <5perc=10, 5-10perc=7, >10perc=3 |
| Ár (hitel nélküli tartomány) | 20% | <130k€=10, 130-150k€=8, 150-170k€=6 |
| Ingatlan méret | 15% | >150m²=10, 120-150m²=7, 100-120m²=5 |
| Kert minősége | 15% | Nagy kert=10, kis kert=6, patio=3 |
| Parkolás/töltés | 10% | Garázs=10, beálló=7, nincs=0 |
| Reptér közelség | 0% | Csak kizáró (>100km → nem jelenik meg) |

**7 pont felett → Telegram értesítés!**
**5-7 pont → Megjelenik a táblázatban, de nincs push értesítés**
**5 pont alatt → Eldobva**

---

## 📧 FORRÁS PORTÁLOK

| Portál | Email feladó | Státusz |
|---|---|---|
| idealista.com | *@idealista.com | ✅ Aktív |
| kyero.com | *@kyero.com | ✅ Aktív |
| thinkspain.com | *@thinkspain.com | ✅ Aktív |
| fotocasa.es | *@fotocasa.es | ⏳ Beállítandó |

---

## 📊 OUTPUT FORMÁTUM

Minden feldolgozott ingatlanhoz:
- Cím / város
- Régió + reptér
- Ár (€) + becsült adóval együtt
- Ingatlan m² + telek m² (ha van)
- Tenger távolság (km)
- Városközpont távolság (perc gyalog / módszer)
- Parkolás típusa
- Jogi státusz (ok / ⚠️ kérdéses / ❌ kizárt)
- Összpontszám (1-10)
- Link az ingatlanhoz
- Email érkezési dátum
