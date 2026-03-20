---
title: Act
emoji: 👀
colorFrom: red
colorTo: gray
sdk: docker
pinned: false
license: mit
short_description: unleash your inner actor!
---

# 🎭 act! - Das feministische Schauspiel-Party-Spiel

**act!** ist ein kreatives, webbasiertes Multiplayer-Partyspiel, das für Schauspiel-Enthusiastinnen, Freundesgruppen und Theater-Workshops entwickelt wurde. Es bringt Improvisation, absurde Rollen und eine gesunde Portion Gesellschaftskritik direkt auf die Smartphones der Spielerinnen.

## 🚀 Features & Funktion

* **Multiplayer in Echtzeit:** Synchronisierte Lobbys für bis zu 5 Spielerinnen (anpassbar) via Redis.
* **3 Spielmodi:** Von simplen Emotionen bis hin zu komplexen Charakter-Szenarien.
* **Zweisprachig (De/En):** Fliegender Wechsel zwischen Deutsch und Englisch. Bei Emotionen wird die jeweilige Übersetzung dezent als Hilfestellung eingeblendet.
* **Screenshot-Export:** Spielerinnen können ihre generierte Szene direkt als PNG auf ihrem Handy speichern, um sie auf Social Media oder in Chat-Gruppen zu teilen.
* **Smart Reconnect:** Fällt das Internet kurz aus oder wird der Browser neu geladen, erkennt das System die Spielerin über ein sicheres, HMAC-signiertes Cookie wieder (24 Stunden gültig) und bringt sie direkt zurück in ihre Lobby.

## 📜 Spielregeln

Eine Spielerin (der Host) erstellt einen "Dressing Room" (Lobby) und legt ein Passwort fest. Die anderen Spielerinnen treten über die 8-stellige ID bei. Sobald der Host das Spiel startet, wählt eine Spielerin (oder die Gruppe gemeinsam) einen der drei Modi:

* **Mode 1 (Emotion & Satz):** Die Spielerin erhält eine zufällige Emotion (z.B. "Wut") und einen absurden oder gesellschaftskritischen Satz (z.B. "Das Patriarchat zerschlägt sich nicht von selbst, reich mir den Hammer."). Sie muss den Satz in der geforderten Emotion vortragen.
* **Mode 2 (Rolle & Satz):** Die Spielerin schlüpft in einen bekannten Charakter (z.B. "Emma Swan" oder "Dr. House") und muss den Satz exakt so vortragen, wie diese Figur es tun würde.
* **Mode 3 (Die absolute Eskalation):** Die Königsdisziplin. Die Spielerin erhält eine Rolle, einen Satz UND eine völlig unpassende Emotion (z.B. "Darth Vader" sagt fröhlich: "Ich liebe Schmetterlinge").

Die Gruppe bewertet die Performance. Bei Erfolg wird der "🌟 Great Job!" Button gedrückt, und das Spiel kehrt zur Modus-Auswahl für die nächste Spielerin zurück.

## 🚧 Technische Grenzen & Architektur

* **Zustandslosigkeit (Stateless):** Der Python/Streamlit-Container hält keine permanenten Daten. Alle Session-Status werden in einer externen **Upstash Redis-Datenbank** gespeichert. Dies erlaubt den reibungslosen Betrieb auf serverless Plattformen wie Koyeb, Render oder Hugging Face.
* **iFrame & Cookie-Restriktionen:** Das Spiel nutzt eine Hybrid-Cookie-Strategie (`SameSite=None; Secure`), um Third-Party-Cookie-Blockaden von Apple (ITP) und Firefox zu umgehen, wenn das Spiel auf Plattformen wie Netlify per iFrame eingebettet wird.
* **Screenshot-Limitierung:** Die Bildgenerierung (`dom-to-image`) passiert komplett im Browser der Nutzerin (Client-Side). Sehr strenge iOS/Safari-Sicherheitseinstellungen können das Herunterladen von via JS generierten Bildern in iFrames gelegentlich blockieren. Nutzerinnen wird in diesem Fall ein Fallback auf Chromium/Firefox empfohlen.
* **Hosting-Cold-Starts:** Bei der Nutzung von kostenlosen Hosting-Plattformen (wie Koyeb Eco-Tier) geht der Container nach 15 Minuten Inaktivität in den Schlafmodus. Der erste Aufruf dauert dann ca. 30-60 Sekunden (Cold Start).

## 🛠️ Tech Stack
* **Frontend & Backend:** Python 3, Streamlit
* **Database:** Redis (Upstash)
* **Security:** Werkzeug (Passwort-Hashing), HMAC (Cookie-Signierung)
* **Containerization:** Docker (Tumbleweed Base Image, Non-Root)
