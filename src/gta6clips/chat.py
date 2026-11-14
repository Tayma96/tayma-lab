"""Twitch sohbetini anonim olarak (giriş gerekmeden) okur ve sohbet patlamalarını yakalar.

Bir yayında komik/çılgın bir şey olduğunda sohbet birkaç saniye içinde KEKW, LUL, ?????, "CLIP IT"
mesajlarıyla dolar. Bu, ses analizinden de, izleyicilerin klip açmasından da daha hızlı bir sinyaldir.
"""
from __future__ import annotations

import logging
import random
import re
import socket
import ssl
import time
from collections import deque

log = logging.getLogger(__name__)

HYPE_TOKENS = {
    "kekw": 1.0, "lul": 0.7, "lulw": 1.0, "omegalul": 1.2, "icant": 1.0, "lmao": 0.8, "lmfao": 1.0,
    "pogchamp": 0.8, "pog": 0.6, "poggers": 0.8, "pogu": 0.8, "monkas": 0.6, "wtf": 0.6, "holy": 0.6,
    "clip": 1.5, "clipped": 1.5, "clipit": 1.5, "kappa": 0.2, "omg": 0.5, "nooo": 0.6, "deadass": 0.4,
}
_WORD = re.compile(r"[a-z]+")


def message_weight(text: str) -> float:
    """1 + heyecan bonusu (en fazla +2). '?????' ve büyük harfle bağırma da sayılır."""
    t = text.lower()
    bonus = sum(HYPE_TOKENS.get(w, 0.0) for w in set(_WORD.findall(t)))
    if "???" in t or "!!!" in t:
        bonus += 0.7
    letters = [ch for ch in text if ch.isalpha()]
    if len(letters) >= 4 and sum(ch.isupper() for ch in letters) / len(letters) > 0.8:
        bonus += 0.5
    return 1.0 + min(2.0, bonus)


class ChatSpikeDetector:
    """Saf mantık (zaman dışarıdan verilir, test edilebilir).
    Son `window` saniyedeki ağırlıklı mesaj miktarını, önceki `baseline` saniyenin ortalamasıyla kıyaslar."""

    def __init__(self, window: float = 6.0, baseline: float = 180.0, ratio: float = 3.0, min_weight: float = 15.0,
                 cooldown: float = 120.0, warmup: float = 60.0):
        self.window, self.baseline, self.ratio = window, baseline, ratio
        self.min_weight, self.cooldown, self.warmup = min_weight, cooldown, warmup
        self.events: deque[tuple[float, float]] = deque()
        self.first_ts: float | None = None
        self.last_trigger = -1e18

    def add(self, ts: float, text: str) -> float | None:
        """Mesajı ekler; patlama varsa gücünü (kaç kat arttığını) döner."""
        if self.first_ts is None:
            self.first_ts = ts
        self.events.append((ts, message_weight(text)))
        while self.events and self.events[0][0] < ts - self.baseline - self.window:
            self.events.popleft()
        if ts - self.first_ts < self.warmup or ts - self.last_trigger < self.cooldown:
            return None
        recent = sum(w for t, w in self.events if t >= ts - self.window)
        older = sum(w for t, w in self.events if t < ts - self.window)
        span = min(self.baseline, max(self.window, ts - self.window - self.first_ts))
        base_per_window = older / max(span / self.window, 1.0)
        if recent >= self.min_weight and recent >= self.ratio * max(base_per_window, 1.0):
            self.last_trigger = ts
            return recent / max(base_per_window, 1.0)
        return None


def parse_privmsg(line: str) -> tuple[str, str] | None:
    """':nick!nick@nick.tmi.twitch.tv PRIVMSG #kanal :mesaj' -> ('kanal', 'mesaj')"""
    if " PRIVMSG #" not in line:
        return None
    try:
        _, rest = line.split(" PRIVMSG #", 1)
        channel, msg = rest.split(" :", 1)
        return channel.strip().lower(), msg.rstrip("\r\n")
    except ValueError:
        return None


class TwitchChat:
    """Tek bağlantıda birçok kanalın sohbetini okur (anonim, sadece okuma)."""

    HOST, PORT = "irc.chat.twitch.tv", 6697

    def __init__(self):
        self.sock: ssl.SSLSocket | None = None
        self.channels: set[str] = set()
        self.buf = ""

    def _connect(self) -> None:
        raw = socket.create_connection((self.HOST, self.PORT), timeout=30)
        self.sock = ssl.create_default_context().wrap_socket(raw, server_hostname=self.HOST)
        self.sock.settimeout(1.0)
        self._send(f"NICK justinfan{random.randint(10000, 99999)}")
        joined, self.channels = self.channels, set()
        self.set_channels(joined)

    def _send(self, line: str) -> None:
        assert self.sock
        self.sock.sendall((line + "\r\n").encode())

    def set_channels(self, wanted: set[str]) -> None:
        wanted = {c.lower() for c in wanted}
        if self.sock is None:
            self.channels = wanted
            return
        for ch in self.channels - wanted:
            self._send(f"PART #{ch}")
        new = sorted(wanted - self.channels)
        for i in range(0, len(new), 15):  # Twitch: 20 JOIN / 10 sn sınırı
            self._send("JOIN " + ",".join(f"#{c}" for c in new[i:i + 15]))
            if i + 15 < len(new):
                time.sleep(8)
        self.channels = wanted

    def poll(self) -> list[tuple[str, str]]:
        """Bekleyen mesajları döner (en fazla ~1 sn bekler). Bağlantı koparsa yeniden bağlanır."""
        if self.sock is None:
            try:
                self._connect()
            except OSError as e:
                log.warning("Sohbete bağlanılamadı (%s), 10 sn sonra tekrar denenecek", e)
                self.sock = None
                time.sleep(10)
                return []
        try:
            data = self.sock.recv(65536).decode("utf-8", errors="ignore")  # type: ignore[union-attr]
            if not data:
                raise ConnectionError("bağlantı kapandı")
        except (socket.timeout, ssl.SSLWantReadError):
            return []
        except (OSError, ConnectionError) as e:
            log.warning("Sohbet bağlantısı koptu (%s), yeniden bağlanılıyor", e)
            self.sock = None
            time.sleep(3)
            return []
        self.buf += data
        lines = self.buf.split("\r\n")
        self.buf = lines.pop()
        out = []
        for line in lines:
            if line.startswith("PING"):
                self._send("PONG" + line[4:])
            elif (m := parse_privmsg(line)) is not None:
                out.append(m)
        return out
