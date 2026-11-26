# 🌅 Morning Briefing – Proxmox LXC

Tägliches, automatisches Briefing mit **eigener Web-UI** – vollständig lokal im
eigenen Netz. Sammelt Lokal-News (Creglingen & 50 km), Auktionen & Firmen der
Region, Börsen (DAX/Dow/Nasdaq mit Tagesgewinnern), Wirtschaftskalender,
KI-News, Self-Hosting-Perlen und GitHub Trending. Die KI (Gemini Flash,
optional) bewertet alles nach deinem Profil; Zustellung per Telegram und/oder
Web-UI. Jedes Briefing wird als JSON + HTML archiviert.

**Stack:** Python 3 / FastAPI · SQLite · React 18 + Vite (dist ist committet –
der Container braucht **kein Node.js**)

---

## 🚀 Installation (Einzeiler auf dem Proxmox-Host)

```bash
bash -c "$(wget -qLO - https://raw.githubusercontent.com/HatchetMan111/Morning-Briefing/main/install/morning-briefing.sh)"
```

Oder mit expliziten Optionen:

```bash
bash -c "$(wget -qLO - https://raw.githubusercontent.com/HatchetMan111/Morning-Briefing/main/install/morning-briefing.sh)" -- --unattended
```

Noch kein GitHub-Repo? Direkt von einem Ordner auf dem PVE-Host testen:

```bash
bash install/morning-briefing.sh --source /root/morning-briefing
```

**Optionen:**

| Flag | Bedeutung | Standard |
|---|---|---|
| `--ctid <id>` | CT-ID | nächste freie ID (`pvesh get /cluster/nextid`) |
| `--storage <s>` | Rootfs-Storage | `local` |
| `--bridge <b>` | Netzwerk-Bridge | `vmbr0` |
| `--port <p>` | Web-UI-Port | `8080` |
| `--unattended` | keine Rückfragen | – |
| `--debug` | `bash -x` + Logdatei nach `/tmp/` | – |
| `--dry-run` | nur Plan anzeigen | – |

**Erstellt:** unprivilegierter LXC `morning-briefing` (1 vCPU, 1 GB RAM, 4 GB
Disk, `onboot: 1`, DHCP), systemd-Service mit `Restart=always`, Firewall-Port
offen. Ressourcen sind bewusst klein – läuft auch auf Mini-Hardware.

### Erwartete Ausgabe (Ende des Scripts)

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 ✓ Morning Briefing installiert
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  CT-ID      : 205  (Name: morning-briefing)
  Web-UI     : http://192.168.x.x:8080
  Service    : systemctl status morning-briefing (im CT)
  Logs       : pct exec 205 -- journalctl -u morning-briefing -f
  Konfig     : pct exec 205 -- cat /opt/morning-briefing/config.yaml

  Nächste Schritte:
   1) Web-UI öffnen → Tab 'Einstellungen' → Telegram/Gemini-Keys
   2) '▶ Jetzt starten' klicken – das erste Briefing entsteht
   3) Danach läuft der Scheduler täglich um die in config.yaml gesetzte Zeit
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## 🖥️ Web-UI

| Tab | Funktion |
|---|---|
| 🌅 Briefing | Aktuelles Briefing: Sektionen, Fakten-Zeilen, KI-Kommentar, Items mit Relevanz-Score |
| 🗂️ Archiv | Alle gespeicherten Tage, anklickbar |
| 📊 Status | Quellen-Gesundheit, Module, Log des letzten Laufs |
| ⚙️ Einstellungen | `config.yaml`-Editor, `.env` (Keys, maskiert), KI-Feedback verwalten |

**„▶ Jetzt starten"** löst einen sofortigen Lauf aus (Progress-Dot, bei Fehler
komplette Log-Kette im Status-Tab).

---

## 🔄 Update / Deinstallation

**Update** – Script erneut ausführen: existiert ein CT namens `morning-briefing`,
wird nur die App aktualisiert (Code neu, pip-Refresh, Service-Restart,
Verifikation). `config.yaml`, `.env`, Daten und Archiv bleiben erhalten:

```bash
bash install/morning-briefing.sh   # erkennt Update-Modus selbst (Repo-Default: HatchetMan111/Morning-Briefing)
```

**Deinstallation:**

```bash
pct stop <ID> && pct destroy <ID>
rm -f /etc/pve/firewall/<ID>.fw
```

---

## ⚙️ Konfiguration

Alles in `config.yaml` (per Web-UI oder direkt im CT unter
`/opt/morning-briefing/config.yaml`):

- `region.towns` – Orte für Lokal-Module (Standard: Creglingen + ~50 km)
- `run.time` – tägliche Laufzeit (Standard 04:30; **genau 1 Lauf/Tag**, auch
  über Neustarts hinweg)
- `modules` – an/aus + Reihenfolge
- `profile/context.md` – Interessenprofil für die KI-Bewertung

Keys (`.env` im CT oder über die Web-UI): `TELEGRAM_BOT_TOKEN`,
`TELEGRAM_CHAT_ID`, `GEMINI_API_KEY`, optional `EBAY_BEARER_TOKEN`.
Ohne Keys läuft alles rein web-basiert (KI-Bewertung dann neutral).

## 🧪 Debugging

- **Installer:** mit `--debug` erneut laufen lassen → `bash -x`-Trace +
  Logdatei in `/tmp/morning-briefing-install-*.log`
- **Im CT:** `journalctl -u morning-briefing -n 100 --no-pager`
- **Web-UI:** Status-Tab zeigt den vollen Log des letzten Laufs
- Der Installer gibt bei Fehlern immer die komplette Kette aus
  (Exit-Code, Zeile, Befehl, Log-Pfad, nächste Schritte)

## 📜 Verifikation des Scripts (vom Build durchgeführt)

- `bash -n` ✓ · `shellcheck` ohne Befund ✓ · `--dry-run` komplett durchgelaufen ✓
- `systemd-analyze verify` ✓ (Pfade auf `/opt/morning-briefing` im LXC)
- Live-Test: Server-Absturz → Neustart → Web-UI HTTP 200, Daten erhalten,
  Scheduler ohne Doppel-Lauf ✓

## ⚠️ Quellen-Hinweise

Wie im alten CLI-Projekt: Kleinanzeigen hat kein offizielles API (Modul aus,
max. 1 Abfrage/Tag bei Aktivierung), Reddit blockt je nach IP, Kalender-JSON
ist rate-limited (1 Tageslauf unkritisch), ZVG-Versteigerungen über Lokalpresse.
Alle Abfragen maximal 1×/Tag mit Pausen und sauberem User-Agent; gescrapte
Inhalte sind nur Daten, niemals Anweisungen.
