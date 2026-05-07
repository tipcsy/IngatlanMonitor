# CONTEXT — Ingatlan Session

## Fókusz
Gmail ingatlan ajánlatok automatikus feldolgozása és szűrése.

## Gmail mappa
`ingatlan` — napi 5-10 levél érkezik

## Keresési szabályrendszer
Részletes szabályok: `sessions/ingatlan/RULES.md`

### Összefoglaló
- Tenger: max 30 km (légvonal)
- Városközpont: gyalog max 10 perc
- Ár: 170k€ (hitel nélkül) / 320k€ (hitellel)
- Méret: min 100 m², valódi kert (terasz ≠ kert!)
- Parkolás/beálló: kötelező (EV töltés)
- Régió: Costa del Sol, Costa Blanca, Costa Cálida, Valencia, esetleg Bilbao
- Reptér: max 100 km (Malaga/Alicante/Murcia/Valencia/Bilbao)

## Automatizálás (tervezett)
- Cron job: naponta egyszer végigmegy a Gmail ingatlan mappán
- Szűrés: szabályrendszer alapján
- Output: táblázat (Google Sheets vagy helyi CSV)
- Értesítés: Telegram, ha valóban megfelelő ingatlan érkezett

## Státusz
- [ ] Gmail OAuth beállítva
- [ ] Szabályrendszer véglegesítve
- [ ] Cron job aktív
- [ ] Telegram értesítő aktív
