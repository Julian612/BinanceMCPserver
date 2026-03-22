# Binance MCP Server

Vollständiger Binance-Trading-MCP-Server auf Basis von **Python / FastMCP / ccxt**.
Deckt alle vier Trading-Bereiche ab: Spot, USD-M Futures, Options und Account/Portfolio.

---

## ⚡ Schnellinstallation (Proxmox LXC / Debian / Ubuntu)

Einzeilen-Installer – einfach in der Root-Shell des LXC ausführen:

```bash
bash -c "$(curl -fsSL https://raw.githubusercontent.com/Julian612/BinanceMCPserver/main/install.sh)"
```

Der Installer erledigt automatisch:
- System-Pakete installieren (python3, git, curl)
- `uv` (Python Package Manager) installieren
- Repository nach `/opt/binance-mcp` clonen
- Virtual Environment anlegen und Dependencies installieren
- API-Keys interaktiv abfragen und in `.env` schreiben
- Systemd-Service einrichten, aktivieren und starten

---

## Verfügbare Tools (22 MCP-Tools)

### Marktdaten (öffentlich – kein API-Key nötig)
| Tool | Beschreibung |
|------|-------------|
| `get_price` | Aktueller Preis für ein Symbol |
| `get_ticker` | Vollständiger 24h-Ticker (bid, ask, volume, change) |
| `get_orderbook` | Order Book (bids/asks, einstellbare Tiefe) |
| `get_ohlcv` | OHLCV-Candlestick-Daten (timestamp, open, high, low, close, volume) |
| `get_markets` | Verfügbare Märkte (spot/future/option) |
| `search_symbols` | Symbol-Suche nach Stichwort |

### Account & Portfolio (API-Key erforderlich)
| Tool | Beschreibung |
|------|-------------|
| `get_balance` | Balance für spot/future/option (nur non-zero Assets) |
| `get_open_orders` | Offene Orders (optional nach Symbol gefiltert) |
| `get_order_history` | Order-Historie |
| `get_positions` | Offene Futures-Positionen mit PnL |
| `get_pnl_summary` | Unrealized PnL über alle Positionen |

### Spot Trading (API-Key erforderlich)
| Tool | Beschreibung |
|------|-------------|
| `place_spot_order` | Market/Limit-Order platzieren |
| `cancel_spot_order` | Order stornieren |
| `cancel_all_spot_orders` | Alle Orders stornieren (optional nach Symbol) |

### USD-M Futures (API-Key erforderlich)
| Tool | Beschreibung |
|------|-------------|
| `place_futures_order` | Futures-Order platzieren (inkl. reduce_only) |
| `cancel_futures_order` | Order stornieren |
| `set_leverage` | Leverage setzen (1–125) |
| `set_margin_mode` | `isolated` oder `cross` |
| `close_position` | Position schließen (teilweise oder vollständig) |

### Options (API-Key erforderlich)
| Tool | Beschreibung |
|------|-------------|
| `get_option_chain` | Alle verfügbaren Kontrakte für ein Underlying |
| `place_options_order` | Options-Order platzieren |
| `cancel_options_order` | Options-Order stornieren |

---

## Manuelle Installation

### Voraussetzungen
- Debian 11/12 oder Ubuntu 22.04/24.04
- Python 3.11+
- [uv](https://docs.astral.sh/uv/) (Package Manager)

### 1. LXC erstellen (Proxmox UI)
```
Template : Debian 12
RAM      : 512 MB (1 GB empfohlen für mehrere MCP-Server)
Disk     : 4 GB
Netzwerk : DHCP oder statische IP
```

### 2. Basis-Setup im LXC
```bash
apt update && apt install -y python3 python3-pip python3-venv git curl ca-certificates
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.bashrc   # oder neu einloggen
```

### 3. Repository klonen & Dependencies installieren
```bash
mkdir -p /opt/binance-mcp
cd /opt/binance-mcp
git clone https://github.com/Julian612/BinanceMCPserver.git .
uv venv
uv sync
```

### 4. API-Keys konfigurieren
```bash
cp .env.example .env
nano .env   # BINANCE_API_KEY und BINANCE_API_SECRET eintragen
chmod 600 .env
```

`.env` Inhalt:
```env
BINANCE_API_KEY=dein_api_key
BINANCE_API_SECRET=dein_api_secret
BINANCE_TESTNET=false
```

### 5. Dedizierten User anlegen (Security)
```bash
useradd --system --no-create-home --shell /bin/false mcpuser
chown -R mcpuser:mcpuser /opt/binance-mcp
```

### 6. systemd Service einrichten
```bash
cp deploy/binance-mcp.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable binance-mcp
systemctl start binance-mcp
systemctl status binance-mcp
```

### 7. Logs prüfen
```bash
journalctl -u binance-mcp -f
```

---

## MCP-Client Konfiguration

### Claude Desktop / Cline / OpenClaw
```json
{
  "mcpServers": {
    "binance": {
      "command": "/opt/binance-mcp/.venv/bin/python",
      "args": ["/opt/binance-mcp/server.py"]
    }
  }
}
```

### Direkter Test (ohne systemd)
```bash
cd /opt/binance-mcp
.venv/bin/python server.py
```

---

## MCP Host LXC – Mehrere Server auf einem Host

Dieser LXC eignet sich als zentraler Host für mehrere MCP-Server.

### Verzeichnisstruktur
```
/opt/mcp/
├── binance-mcp/          # Dieser Server
├── <weiterer-mcp>/       # Platz für weitere Server
└── shared/
    └── logs/             # Zentrale Log-Ablage
```

### Ressourcen-Empfehlung
| Ressource | Empfehlung |
|-----------|-----------|
| RAM | 1 GB (für 3–5 MCP-Server) |
| Disk | 8 GB |
| CPU | 1–2 vCores |
| Netzwerk | Feste IP empfohlen (z.B. `192.168.x.50`) |

### Zentral-Management via `deploy/manage.sh`
```bash
# Alle Services starten/stoppen/neustarten
/opt/binance-mcp/deploy/manage.sh start all
/opt/binance-mcp/deploy/manage.sh status all
/opt/binance-mcp/deploy/manage.sh logs binance-mcp

# Skript global verfügbar machen
ln -s /opt/binance-mcp/deploy/manage.sh /usr/local/bin/mcp-manage
mcp-manage status all
```

---

## Projektstruktur

```
binance-mcp/
├── install.sh                  # ⚡ Proxmox-style One-Liner Installer
├── server.py                   # Einstiegspunkt (stdio MCP)
├── pyproject.toml
├── .env.example
├── .gitignore
├── binance_mcp/
│   ├── client.py               # ccxt Exchange-Instanzen (spot/futures/options)
│   ├── tools/
│   │   ├── market_data.py      # Öffentliche Marktdaten
│   │   ├── spot.py             # Spot Trading
│   │   ├── futures.py          # USD-M Futures
│   │   ├── options.py          # Options
│   │   └── account.py          # Account & Portfolio
│   └── utils/
│       └── formatting.py       # Response-Formatierung
└── deploy/
    ├── binance-mcp.service     # systemd Unit File
    └── manage.sh               # Multi-Service Manager
```

---

## Sicherheitshinweise

- API-Keys werden **niemals** in Responses zurückgegeben
- `.env` immer auf `chmod 600` setzen
- Service läuft als unprivilegierter `mcpuser` (kein Shell-Login)
- `enableRateLimit=True` verhindert Rate-Limit-Bans bei Binance
- Für Tests und Entwicklung: `BINANCE_TESTNET=true` setzen

---

## Testnet

Binance Testnet für risikofreies Testen:
1. Account anlegen: [testnet.binance.vision](https://testnet.binance.vision)
2. In `.env` setzen: `BINANCE_TESTNET=true`
3. Service neu starten: `systemctl restart binance-mcp`

---

## Stack

- **Python 3.11+** – Runtime
- **FastMCP** – MCP Server Framework
- **ccxt** – Unified Crypto Exchange Library (Binance API)
- **python-dotenv** – Environment Variable Management
- **uv** – Python Package Manager
