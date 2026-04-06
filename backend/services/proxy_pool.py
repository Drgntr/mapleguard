"""
Proxy Pool — Round-robin rotation with health tracking.

Sources (checked in order):
  1. PROXY_LIST env var (comma-separated URLs)
  2. Proxy file: PROXY_FILE_PATH env or "Webshare 100 proxies.txt" in project root
     Format (Webshare): ip:port:user:pass per line
  3. PROXY_CONFIG_PATH env var (JSON: {"proxies": ["http://..."]})
"""

import json
import os
import time
from typing import Optional


def _find_project_root() -> str:
    """Find the project root (MapleGuard/) by walking up from this file's path."""
    current = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    # backend/ -> look for MapleGuard/
    if os.path.basename(current) == "backend":
        parent = os.path.dirname(current)
        if os.path.basename(parent) == "MapleGuard":
            return parent
    return current


class ProxyPool:
    def __init__(self):
        self._proxies: list[dict] = []  # {"url": str, "failures": int, "cooldown_until": float}
        self._index = 0
        self._loaded = False

    def _clean(self, s: str) -> str:
        """Remove all non-printable chars from a string."""
        return "".join(c for c in s if c.isprintable())

    def load(self):
        """Load proxies from env, Webshare file, or config file."""
        if self._loaded:
            return

        # 1. Try env var first (comma or newline-separated full URLs)
        proxy_list = os.environ.get("PROXY_LIST", "").strip()
        if proxy_list:
            urls = []
            for line in proxy_list.replace("\n", ",").split(","):
                url = self._clean(line.strip())
                if url and "http" not in url:
                    url = f"http://{url}"
                if url:
                    urls.append(url)
            self._proxies = [{"url": u, "failures": 0, "cooldown_until": 0} for u in urls]
            self._loaded = True
            print(f"[ProxyPool] Loaded {len(self._proxies)} proxies from PROXY_LIST")
            return

        # 2. Try Webshare proxy file
        proxy_file_path = os.environ.get("PROXY_FILE_PATH", "").strip()
        if not proxy_file_path:
            # Default: search for "Webshare 100 proxies.txt" in project root
            root = _find_project_root()
            candidates = [
                os.path.join(root, "Webshare 100 proxies.txt"),
                os.path.join(root, "webshare 100 proxies.txt"),
                os.path.join(root, "proxies.txt"),
            ]
            for c in candidates:
                if os.path.exists(c):
                    proxy_file_path = c
                    break

        if proxy_file_path and os.path.exists(proxy_file_path):
            try:
                with open(proxy_file_path, "r") as f:
                    lines = f.readlines()
                urls = []
                for line in lines:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    # Webshare format: ip:port:user:pass
                    parts = line.split(":")
                    if len(parts) == 4:
                        ip, port, user, pwd = parts
                        url = f"http://{self._clean(user)}:{self._clean(pwd)}@{self._clean(ip)}:{self._clean(port)}"
                        urls.append(url)
                    elif len(parts) == 2:
                        # Just ip:port
                        url = f"http://{self._clean(parts[0])}:{self._clean(parts[1])}"
                        urls.append(url)
                    else:
                        continue

                self._proxies = [{"url": u, "failures": 0, "cooldown_until": 0} for u in urls]
                self._loaded = True
                print(f"[ProxyPool] Loaded {len(self._proxies)} proxies from {proxy_file_path}")
                return
            except Exception as e:
                print(f"[ProxyPool] Failed to load proxy file: {e}")

        # 3. Try JSON config file
        config_path = os.environ.get("PROXY_CONFIG_PATH", "").strip()
        if config_path and os.path.exists(config_path):
            try:
                with open(config_path, "r") as f:
                    data = json.load(f)
                urls = data.get("proxies", [])
                self._proxies = [{"url": self._clean(u), "failures": 0, "cooldown_until": 0} for u in urls]
                self._loaded = True
                print(f"[ProxyPool] Loaded {len(self._proxies)} proxies from {config_path}")
                return
            except Exception as e:
                print(f"[ProxyPool] Failed to load config file: {e}")

        print("[ProxyPool] No proxies configured — running without proxy rotation")

    def get_proxy(self) -> Optional[str]:
        """Get next healthy proxy URL, or None if no proxy available."""
        if not self._proxies:
            return None

        now = time.time()
        for _ in range(len(self._proxies)):
            idx = self._index % len(self._proxies)
            self._index += 1
            p = self._proxies[idx]
            if now >= p["cooldown_until"]:
                return p["url"]
            self._index += 1

        return None

    def get_proxy_dict(self) -> dict:
        """Get proxy in httpx-compatible format."""
        url = self.get_proxy()
        if url:
            return {"http://": url, "https://": url}
        return {}

    def report_success(self, url: str):
        for p in self._proxies:
            if p["url"] == url:
                p["failures"] = 0
                p["cooldown_until"] = 0
                break

    def report_failure(self, url: str, cooldown: int = 30):
        for p in self._proxies:
            if p["url"] == url:
                p["failures"] += 1
                p["cooldown_until"] = time.time() + cooldown
                print(f"[ProxyPool] Proxy {url[:40]}... failure #{p['failures']}, cooldown {cooldown}s")
                break

    @property
    def size(self) -> int:
        return len(self._proxies)

    @property
    def available(self) -> int:
        now = time.time()
        return sum(1 for p in self._proxies if now >= p["cooldown_until"])

    def status(self) -> dict:
        now = time.time()
        return {
            "total": len(self._proxies),
            "available": sum(1 for p in self._proxies if now >= p["cooldown_until"]),
            "on_cooldown": sum(1 for p in self._proxies if now < p["cooldown_until"]),
        }


# Singleton
proxy_pool = ProxyPool()
