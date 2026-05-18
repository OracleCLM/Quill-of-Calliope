# Calliope.AI — systemd User Units (optional auto-start)

Doc-only. Operator decides whether to install.

## Prerequisites

```bash
systemctl --user daemon-reload
systemctl --user --version   # systemd 232+
loginctl enable-linger $USER # allow user units to survive logout
```

## Unit: calliope-llm-gateway.service

**Path**: `~/.config/systemd/user/calliope-llm-gateway.service`

```ini
[Unit]
Description=Calliope.AI LLM Gateway HTTP (port 8766)
After=network.target

[Service]
Type=simple
WorkingDirectory=/home/nic/Scrivania/Calliope.AI
ExecStart=/home/nic/anaconda3/bin/python3 scripts/llm_gateway_http.py
Restart=on-failure
RestartSec=5
StandardOutput=append:/tmp/calliope_llm_gateway.log
StandardError=append:/tmp/calliope_llm_gateway.log

[Install]
WantedBy=default.target
```

## Unit: calliope-mascot-ws.service

**Path**: `~/.config/systemd/user/calliope-mascot-ws.service`

```ini
[Unit]
Description=Calliope.AI Mascot WebSocket Server (port 8767)
After=network.target calliope-llm-gateway.service
Wants=calliope-llm-gateway.service

[Service]
Type=simple
WorkingDirectory=/home/nic/Scrivania/Calliope.AI
ExecStart=/home/nic/anaconda3/bin/python3 scripts/mascot_ws_server.py --port 8767
Restart=on-failure
RestartSec=3
StandardOutput=append:/tmp/calliope_mascot_ws.log
StandardError=append:/tmp/calliope_mascot_ws.log

[Install]
WantedBy=default.target
```

## Install commands (when operator ready)

```bash
mkdir -p ~/.config/systemd/user/
# copy the .service files above
systemctl --user daemon-reload
systemctl --user enable --now calliope-llm-gateway
systemctl --user enable --now calliope-mascot-ws
systemctl --user status calliope-llm-gateway calliope-mascot-ws
```

## Uninstall

```bash
systemctl --user disable --now calliope-llm-gateway calliope-mascot-ws
rm ~/.config/systemd/user/calliope-*.service
systemctl --user daemon-reload
```

## Alternative: manual scripts (no systemd)

```bash
scripts/start_all_calliope_daemons.sh   # start both
scripts/stop_all_calliope_daemons.sh    # stop both
scripts/start_mascot_ws.sh --status     # check WS health
```
