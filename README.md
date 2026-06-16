# Streamplan-Website (HandOfMemes)

Eine sich **automatisch aktualisierende** Website, die den Streamplan aus
`r/HandOfMemes` anzeigt – als legaler Ersatz dafür, den Discord-Channel
auszulesen (für den du keine Rechte hast).

Datenquelle ist Reddit, das eine offene, erlaubte Schnittstelle hat. Ein
GitHub-Action-Lauf holt regelmäßig die neuesten Posts und baut daraus eine
fertige Seite, die über GitHub Pages kostenlos online steht.

---

## Schnellstart (ca. 10 Minuten, alles kostenlos)

### 1. Repository anlegen
- Auf GitHub ein neues, **öffentliches** Repository erstellen (z. B. `streamplan`).
- Diese Dateien hochladen, mit genau dieser Struktur:

```
build.py
.github/
  workflows/
    build.yml      <-  (die Datei build.yml gehört hierhin)
```

> Wichtig: `build.yml` muss in den Ordner `.github/workflows/`.
> `build.py` bleibt im Hauptverzeichnis.

### 2. GitHub Pages aktivieren
- Im Repo: **Settings → Pages**
- Bei **Source** → **GitHub Actions** auswählen. Mehr ist hier nicht nötig.

### 3. (Empfohlen) Reddit-Zugang einrichten – für Zuverlässigkeit
Ohne diesen Schritt funktioniert die Seite oft trotzdem, aber Reddit blockt
Anfragen aus Rechenzentren (wie GitHub) manchmal. Mit einem kostenlosen
Reddit-App-Zugang läuft es stabil:

1. Eingeloggt auf <https://www.reddit.com/prefs/apps> ganz unten auf
   **„create another app…"** klicken.
2. Typ **„script"** wählen, einen Namen vergeben, bei „redirect uri"
   `http://localhost:8080` eintragen, dann **create app**.
3. Du bekommst zwei Werte:
   - die **Client-ID** (steht klein direkt unter dem App-Namen)
   - das **Secret**
4. Im Repo: **Settings → Secrets and variables → Actions → New repository secret**
   und diese drei anlegen:

   | Name | Wert |
   |------|------|
   | `REDDIT_CLIENT_ID` | deine Client-ID |
   | `REDDIT_CLIENT_SECRET` | dein Secret |
   | `REDDIT_USER_AGENT` | z. B. `streamplan-mirror/1.0 (by /u/DEINNAME)` |

### 4. Loslegen
- Reiter **Actions** → den Workflow auswählen → **Run workflow** (manuell starten).
- Danach läuft er automatisch alle 30 Minuten.
- Deine Seite ist erreichbar unter:
  `https://DEINNAME.github.io/streamplan/`

---

## Anpassen

Oben in `build.py` im Abschnitt **KONFIGURATION**:

- `SUBREDDIT` – aus welchem Subreddit gelesen wird.
- `FLAIR_FILTER` – nur Posts mit diesem Flair (Standard: `streamplan`). Das ist
  zuverlässiger als der Titel, weil im Subreddit alle relevanten Posts das
  graue „Streamplan"-Label tragen – auch die ohne „Streamplan" im Titel.
  Auf `""` setzen, um **alle** neuen Posts zu zeigen.
- `MAX_POSTS` – wie viele Posts angezeigt werden.
- `AUTO_RELOAD_MINUTES` – wie oft eine offene Seite sich selbst neu lädt.

Das Aktualisierungs-Intervall (alle 30 Min.) änderst du in `build.yml` bei
`cron`.

---

## Lokal testen (optional)

```bash
pip install requests
python build.py
# öffne danach public/index.html im Browser
```

Lokal funktioniert auch ohne die Reddit-Secrets (es wird der öffentliche
Endpunkt genutzt).

---

## Hinweise

- Es werden nur **öffentliche** Reddit-Posts gelesen – kein Login, kein Bot
  im Discord, kein Verstoß gegen Nutzungsbedingungen.
- Die Seite zeigt immer den aktuellen Stand des letzten erfolgreichen Laufs.
  Schlägt ein Lauf fehl (z. B. Reddit kurz nicht erreichbar), bleibt die
  vorige Version online.
