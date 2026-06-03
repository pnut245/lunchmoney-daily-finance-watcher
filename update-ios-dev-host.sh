#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

host_ip="$(ipconfig getifaddr en0 2>/dev/null || true)"
if [ -z "$host_ip" ]; then
  host_ip="$(ipconfig getifaddr en1 2>/dev/null || true)"
fi

if [ -z "$host_ip" ]; then
  echo "Could not detect a LAN IP from en0 or en1." >&2
  exit 1
fi

cat > ios/Shared/DevHostConfig.swift <<EOF
import Foundation

enum DevHostConfig {
    static let currentLANIP = "$host_ip"
    static let serverPort = 8422

    static var suggestedDeviceURLString: String {
        "http://\\(currentLANIP):\\(serverPort)/data/widget_snapshot.json"
    }
}
EOF

echo "Updated ios/Shared/DevHostConfig.swift with LAN IP: $host_ip"
