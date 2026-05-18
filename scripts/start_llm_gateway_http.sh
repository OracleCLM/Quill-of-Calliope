#!/usr/bin/env bash
# Start Calliope LLM Gateway HTTP bridge (port 8766)
cd /home/nic/Scrivania/Calliope.AI
python3 scripts/llm_gateway_http.py --daemon "$@"
echo "Gateway: http://localhost:8766/health"
