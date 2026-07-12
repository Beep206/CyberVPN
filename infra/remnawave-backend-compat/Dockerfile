FROM remnawave/backend:2.8.0@sha256:cbc6d2ea0a84d8414dec565bb9ce299a3318b9e5297496baf8efcff2a1e66c65

LABEL org.opencontainers.image.title="CyberVPN Remnawave backend compatibility"
LABEL org.opencontainers.image.description="Remnawave 2.8.0 backend with VLESS RAW Vision per-client flow compatibility patch"
LABEL org.opencontainers.image.version="2.8.0-raw-vision-flow.2"
LABEL org.opencontainers.image.base.name="remnawave/backend:2.8.0"
LABEL org.opencontainers.image.base.digest="sha256:cbc6d2ea0a84d8414dec565bb9ce299a3318b9e5297496baf8efcff2a1e66c65"

COPY patch-xray-config-validator.mjs /usr/local/share/cybervpn/remnawave-backend-compat/patch-xray-config-validator.mjs

RUN node /usr/local/share/cybervpn/remnawave-backend-compat/patch-xray-config-validator.mjs \
    && node -e "const fs = require('node:fs'); const p = '/opt/app/dist/src/common/helpers/xray-config/xray-config.validator.js'; const s = fs.readFileSync(p, 'utf8'); const patchedLine = 'const vlessFlow = (0, get_vless_flow_1.getVlessFlow)(inbound);'; const cleanupLine = 'delete inbound.settings.flow;'; const oldBlock = 'inbound.settings.clients.push({\\n                        id: user.vlessUuid,\\n                        email: user.tId.toString(),\\n                    });'; if ((s.split(patchedLine).length - 1) !== 1) { throw new Error('patched per-client VLESS flow line is missing or ambiguous'); } if ((s.split(cleanupLine).length - 1) !== 1) { throw new Error('patched top-level flow cleanup is missing or ambiguous'); } if (s.includes(oldBlock)) { throw new Error('unpatched VLESS client push block remains'); }"
