# Binance MCP Server

Ein vollständiger Binance Trading MCP-Server auf Basis von Python/FastMCP und ccxt.
Deckt alle vier Trading-Bereiche ab: Spot, USD-M Futures, Options und Marktdaten.
Läuft via stdio und ist optimiert für den Einsatz auf einem Proxmox LXC (Debian/Ubuntu).

## Verfügbare Tools

### Marktdaten (öffentlich – kein API Key erforderlich)
| Tool | Beschreibung |
|---|---|
| `get_price` | Aktueller Preis für ein Symbol |
| `get_ticker` | Vollständiger Ticker (Bid/Ask, Volumen, 24h-Änderung) |
| `get_orderbook` | Order Book (Bids/Asks) |
| `get_ohlcv` | Candlestick-Daten (OHLCV) |
| `get_markets` | Verfügbare Märkte (spot/future/option) |
| `search_symbols` | Symbol-Suche |

### Account & Portfolio (API Key erforderlich)
| Tool | Beschreibung |
|---|---|
| `get_balance` | Guthaben für spot/future/option |
| `get_open_orders` | Offene Orders |
| `get_order_history` | Order-History |
| `get_positions` | Offene Futures-Positionen mit PnL |
| `get_pnl_summary` | Unrealized + Realized PnL Zusammenfassung |

### Spot Trading (API Key + Trading-Berechtigung)
| Tool | Beschreibung |
|---|---|
| `place_spot_order` | Order platzieren (market/limit) |
| `cancel_spot_order` | Order stornieren |
| `cancel_all_spot_orders` | Alle Orders stornieren |

### USD-M Futures Trading
| Tool | Beschreibung |
|---|---|
| `place_futures_order` | Futures Order platzieren |
| `cancel_futures_order` | Order stornieren |
| `set_leverage` | Leverage setzen (1–125) |
| `set_margin_mode` | Margin-Modus: isolated/cross |
| `close_position` | Position schliessen |

### Options Trading
| Tool | Beschreibung |
|---|---|
| `get_option_chain` | Alle Options für ein Underlying (z.B. BTC) |
| `place_options_order` | Options Order platzieren |
| `cancel_options_order` | Options Order stornieren |

---

## Proxmox LXC Setup

### 1. LXC erstellen (Proxmox UI)

- **Template:** Debian 12 (oder Ubuntu 22.04/24.04)
- **RAM:** 512 MB (empfohlen: 1 GB für MCP Host mit mehreren Servern)
- **Disk:** 4 GB (empfohlen: 8 GB)
- **CPU:** 1 vCore (empfohlen: 2)
- **Netzwerk:** DHCP oder statische IP (feste IP für MCP Host empfohlen)
- **Features:** Nesting aktiviert (für systemd)

### 2. Basis-Setup im LXC

```bash
apt update && apt install -y python3 python3-pip curl git build-essential
curl -LsSf https://astral.sh/uv/install.sh | sh
source $HOME/.local/bin/env   # oder neu einloggen
```

### 3. Deployment

```bash
mkdir -p /opt/binance-mcp
cd /opt/binance-mcp
git clone <repo-url> .
uv venv
uv sync
```

### 4. API Keys konfigurieren

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

### 5. Systemuser anlegen (Security)

```bash
useradd -r -s /bin/false -d /opt/binance-mcp mcpuser
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

### 7. MCP Client Konfiguration (Claude Desktop / Cline / etc.)

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

### 8. Logs prüfen

```bash
journalctl -u binance-mcp -f
journalctl -u binance-mcp --since "1 hour ago"
```

---

## MCP Host LXC – Zentraler Host für mehrere MCP Server

Dieser LXC dient als Heimat für alle MCP Server. Die Verzeichnisstruktur
erlaubt einfaches Hinzufügen weiterer Server.

### Verzeichnisstruktur

```
/opt/mcp/
├── binance-mcp/          # Dieser Server
├── <weiterer-mcp>/       # Platz für weitere MCP Server
└── shared/
    └── logs/             # Zentrale Log-Ablage
```

Setup:

```bash
mkdir -p /opt/mcp/shared/logs
ln -s /opt/binance-mcp /opt/mcp/binance-mcp
```

### Zentrales Management-Script

Das Script `deploy/manage.sh` verwaltet alle MCP-Services:

```bash
chmod +x /opt/binance-mcp/deploy/manage.sh
cp /opt/binance-mcp/deploy/manage.sh /opt/mcp/manage.sh

# Verwendung
/opt/mcp/manage.sh status
/opt/mcp/manage.sh start all
/opt/mcp/manage.sh restart binance-mcp
/opt/mcp/manage.sh stop all
```

Um weitere Services hinzuzufügen, die `SERVICES`-Array-Variable in `manage.sh` erweitern:
```bash
SERVICES=("binance-mcp" "neuer-mcp-service")
```

### Ressourcen-Empfehlung für MCP Host LXC

| Ressource | Minimum | Empfohlen (3–5 Server) |
|---|---|---|
| RAM | 512 MB | 1 GB |
| Disk | 4 GB | 8 GB |
| CPU | 1 vCore | 2 vCores |
| Netzwerk | DHCP | Feste IP (z.B. 192.168.x.50) |

---

## Entwicklung & Testnet

### Testnet aktivieren

In `.env`:
```env
BINANCE_TESTNET=true
```

Testnet API Keys von [testnet.binance.vision](https://testnet.binance.vision) holen.

### Lokaler Start (ohne systemd)

```bash
cd /opt/binance-mcp
uv run python server.py
```

### Abhängigkeiten aktualisieren

```bash
uv sync --upgrade
```

---

## Sicherheitshinweise

- API Keys **niemals** in Logs, Git oder Responses ausgeben
- `.env` Datei mit `chmod 600 .env` schützen
- Für reine Marktdaten-Abfragen keinen API Key konfigurieren
- Futures- und Options-Trading nur mit explizit freigeschalteten API Keys
- Testnet für alle Entwicklungs- und Testzwecke nutzen
- Den `mcpuser` ohne Login-Shell anlegen (`/bin/false`)
