#!/usr/bin/env python3
"""Keep public relay discovery accurate and replace failed Quick Tunnels."""
from __future__ import annotations

import json
import os
from pathlib import Path
import queue
import re
import signal
import subprocess
import threading
import time
from urllib.request import getproxies


class HealthWatch:
    """Withdraw immediately on failure; recycle after persistent failure."""
    def __init__(self, now: float, startup_timeout: float = 180) -> None:
        self.started = now
        self.startup_timeout = startup_timeout
        self.failures = 0
        self.ever_online = False

    def observe(self, healthy: bool, now: float) -> tuple[bool, bool]:
        if healthy:
            self.ever_online = True
            self.failures = 0
        else:
            self.failures += 1
        restart = not healthy and (
            (self.ever_online and self.failures >= 3)
            or (not self.ever_online and now - self.started >= self.startup_timeout)
        )
        return healthy, restart


def healthy_relay(document: object) -> bool:
    return isinstance(document, dict) and (
        document.get('ok') is True
        and document.get('service') == 'cuktech-ap01-fds-relay'
        and document.get('api_version') == 1
        and document.get('firmware') == '1.0.2_0031'
    )


def public_health(url: str) -> bool:
    # Validate JSON as well as HTTP status. LaunchAgents do not inherit the
    # terminal's proxy variables; getproxies also reads macOS System Settings.
    doh = os.environ.get('CUKTECH_RELAY_DOH_URL', 'https://cloudflare-dns.com/dns-query')
    routes = [['--noproxy', '*', '--doh-url', doh], ['--noproxy', '*']]
    proxy = os.environ.get('CUKTECH_RELAY_HEALTH_PROXY') or getproxies().get('https')
    if proxy and url.startswith('https://'):
        routes.insert(0, ['--proxy', proxy, '--noproxy', ''])
    for extra in routes:
        try:
            result = subprocess.run(
                ['/usr/bin/curl', '--http1.1', '-fsS', '--connect-timeout', '8',
                 '--max-time', '20', *extra, url + '/health'],
                capture_output=True, timeout=22, check=False,
            )
            if result.returncode == 0 and healthy_relay(json.loads(result.stdout)):
                return True
        except (OSError, ValueError, subprocess.TimeoutExpired):
            pass
    return False


class Discovery:
    def __init__(self) -> None:
        self.gist = os.environ['CUKTECH_RELAY_DISCOVERY_GIST']
        self.gh = os.environ.get('CUKTECH_GH', '/opt/homebrew/bin/gh')
        self.path = Path.home() / 'Library/Application Support/CUKTECH Screen Controller/fds-relay/cuktech-relay-service.json'
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.last_state: tuple[bool, str] | None = None
        self.last_publish = 0.0

    def publish(self, online: bool, url: str = '') -> None:
        state = (online, url if online else '')
        # A short lease also detects host sleep and complete network loss.
        if state == self.last_state and (not online or time.monotonic() - self.last_publish < 90):
            return
        now = int(time.time())
        payload = {
            'enabled': online, 'url': state[1], 'api_version': 1,
            'checked_at': now, 'expires_at': now + 240 if online else now,
            'message': 'Gateway-free AP01 onboarding relay is online' if online else
            'Gateway-free AP01 onboarding relay is temporarily offline; please retry later',
        }
        self.path.write_text(json.dumps(payload, indent=2) + '\n')
        self.path.chmod(0o600)
        try:
            result = subprocess.run(
                [self.gh, 'gist', 'edit', self.gist, '--filename', self.path.name, str(self.path)],
                capture_output=True, timeout=20, check=False,
            )
            if result.returncode != 0:
                print('Discovery publication failed; will retry', flush=True)
                return
        except (OSError, subprocess.TimeoutExpired):
            print('Discovery publication timed out; will retry', flush=True)
            return
        self.last_state = state
        self.last_publish = time.monotonic()
        print('Discovery ' + ('online: ' + state[1] if online else 'offline'), flush=True)


def main() -> None:
    stop = threading.Event()
    for sig in (signal.SIGTERM, signal.SIGINT):
        signal.signal(sig, lambda *_: stop.set())
    discovery = Discovery()
    protocol = os.environ.get('CUKTECH_RELAY_PROTOCOL', 'auto')
    if protocol not in {'auto', 'quic', 'http2'}:
        raise ValueError('CUKTECH_RELAY_PROTOCOL must be auto, quic, or http2')
    origin = os.environ.get('CUKTECH_FDS_RELAY_ORIGIN', 'http://127.0.0.1:8790')
    cloudflared = os.environ.get('CUKTECH_CLOUDFLARED', str(Path.home() / '.local/bin/cloudflared'))
    env = {k: v for k, v in os.environ.items() if k.lower() not in {'http_proxy', 'https_proxy', 'all_proxy'}}
    try:
        discovery.publish(False)
        while not stop.is_set():
            if not public_health(origin):
                discovery.publish(False)
                stop.wait(15)
                continue
            child = subprocess.Popen(
                [cloudflared, 'tunnel', '--protocol', protocol, '--no-autoupdate', '--url', origin],
                env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
            )
            lines: queue.Queue[str] = queue.Queue()

            def drain(stream=child.stdout) -> None:
                assert stream is not None
                for line in stream:
                    print(line.rstrip(), flush=True)
                    match = re.search(r'https://[-a-z0-9]+\.trycloudflare\.com', line)
                    if match:
                        lines.put(match.group())

            reader = threading.Thread(target=drain, daemon=True)
            reader.start()
            watch = HealthWatch(time.monotonic())
            url = ''
            next_check = 0.0
            try:
                while not stop.is_set() and child.poll() is None:
                    try:
                        url = lines.get(timeout=1)
                        next_check = 0
                    except queue.Empty:
                        pass
                    if time.monotonic() < next_check:
                        continue
                    online, restart = watch.observe(bool(url) and public_health(url), time.monotonic())
                    discovery.publish(online, url)
                    if restart:
                        print('Public health failed repeatedly; replacing tunnel', flush=True)
                        break
                    next_check = time.monotonic() + 20
            finally:
                discovery.publish(False)
                child.terminate()
                try:
                    child.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    child.kill()
                    child.wait(timeout=5)
                reader.join(timeout=2)
                if child.stdout:
                    child.stdout.close()
            stop.wait(15)
    finally:
        discovery.publish(False)


if __name__ == '__main__':
    main()
