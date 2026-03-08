"""
Filtro de texto inteligente para mensajes TTS.

Elimina automáticamente:
  - Emojis Unicode (Windows, YouTube, Twitch nativos, todos los SO)
  - Emotes de Twitch: descargados automaticamente desde BTTV, FFZ y 7TV (sin auth)
  - Emojis de YouTube en formato :texto:
  - Palabras extra configuradas por el usuario

Las fuentes de emotes se descargan en background al arranque,
se cachean en config/emotes_cache.json y se refrescan cada 24h.

Configurable via app_settings.json -> "text_filter":
  {
    "remove_unicode_emoji": true,
    "remove_twitch_emotes": true,
    "remove_colon_emotes": true,
    "extra_words": ["MiEmote", "OtroEmote"],
    "cache_ttl_hours": 24
  }
"""

import re
import json
import time
import threading
import urllib.request
import os
from typing import Optional

# -- Unicode emoji regex -------------------------------------------------------
_UNICODE_EMOJI_RE = re.compile(
    "["
    "\U0001F600-\U0001F64F"
    "\U0001F300-\U0001F5FF"
    "\U0001F680-\U0001F6FF"
    "\U0001F700-\U0001F77F"
    "\U0001F780-\U0001F7FF"
    "\U0001F800-\U0001F8FF"
    "\U0001F900-\U0001F9FF"
    "\U0001FA00-\U0001FA6F"
    "\U0001FA70-\U0001FAFF"
    "\U00002702-\U000027B0"
    "\U000024C2-\U0001F251"
    "\U0001F1E0-\U0001F1FF"
    "\U00002500-\U00002BEF"
    "\U00002300-\U000023FF"
    "\U00002B50-\U00002B55"
    "\U0000200D"
    "\U0000FE0F"
    "\U000020E3"
    "]+",
    re.UNICODE,
)

# -- Emojis :nombre: (YouTube custom emojis, bots) ----------------------------
# YouTube usa slug largos tipo :person-turquoise-writing-headphones: (hasta ~50 chars)
_COLON_EMOTE_RE = re.compile(r':[a-zA-Z0-9_\-]{2,64}:')

# -- Espacios multiples --------------------------------------------------------
_MULTI_SPACE_RE = re.compile(r'  +')

# -- Semilla minima (fallback si no hay red ni cache) --------------------------
_SEED_EMOTES = {
    "Kappa", "KappaHD", "KappaPride", "PogChamp", "Pog", "PogU",
    "LUL", "LULW", "KEKW", "OMEGALUL", "TriHard", "BibleThump",
    "4Head", "EleGiggle", "DansGame", "BabyRage", "ResidentSleeper",
    "NotLikeThis", "WutFace", "FeelsBadMan", "FeelsGoodMan",
    "monkaS", "monkaW", "Sadge", "COPIUM", "HOPIUM", "peepoHappy",
    "peepoSad", "catJAM", "HYPERS", "GIGACHAD", "Clap", "GG",
    "xqcL", "PauseChamp", "widepeepoHappy", "AYAYA", "WeirdChamp",
}

# -- Rutas ---------------------------------------------------------------------
_HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_CACHE_PATH = os.path.join(_HERE, "config", "emotes_cache.json")

# -- Fuentes publicas globales (sin autenticacion) ---------------------------
_SOURCES_GLOBAL = {
    "bttv_global": "https://api.betterttv.net/3/cached/emotes/global",
    "ffz_global":  "https://api.frankerfacez.com/v1/set/global",
    "7tv_global":  "https://7tv.io/v3/emote-sets/global",
}


def _build_channel_sources(channels: list) -> dict:
    """URLs de emotes para una lista de canales [{id, name}, ...]."""
    sources = {}
    for ch in channels:
        cid  = ch.get("id", "").strip()
        name = ch.get("name", "").strip().lower()
        tag  = name or cid  # etiqueta unica para el log
        if cid:
            sources[f"bttv_{tag}"] = f"https://api.betterttv.net/3/cached/users/twitch/{cid}"
            sources[f"7tv_{tag}"]  = f"https://7tv.io/v3/users/twitch/{cid}"
        if name:
            sources[f"ffz_{tag}"]  = f"https://api.frankerfacez.com/v1/room/{name}"
    return sources


def _fetch_json(url: str, timeout: int = 8):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "NopoloTTS/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except Exception:
        return None


def _extract_emote_names(source_key: str, data) -> set:
    names = set()
    try:
        if source_key in ("bttv_global",):
            # [{"code": "KEKW", ...}, ...]
            for e in data:
                code = e.get("code", "")
                if code:
                    names.add(code)
        elif source_key == "bttv_channel":
            # {"channelEmotes": [...], "sharedEmotes": [...]}
            for key in ("channelEmotes", "sharedEmotes"):
                for e in data.get(key, []):
                    code = e.get("code", "")
                    if code:
                        names.add(code)
        elif source_key in ("ffz_global", "ffz_channel"):
            # {"sets": {"id": {"emoticons": [{"name": ...}]}}}
            for s in data.get("sets", {}).values():
                for e in s.get("emoticons", []):
                    name = e.get("name", "")
                    if name:
                        names.add(name)
        elif source_key == "7tv_global":
            # {"emotes": [{"name": ...}, ...]}
            for e in data.get("emotes", []):
                name = e.get("name", "")
                if name:
                    names.add(name)
        elif source_key == "7tv_channel":
            # {"emote_set": {"emotes": [{"name": ...}]}}
            for e in data.get("emote_set", {}).get("emotes", []):
                name = e.get("name", "")
                if name:
                    names.add(name)
    except Exception:
        pass
    return names


def _load_cache():
    """Devuelve (emotes_set, timestamp). timestamp=0 si no hay cache."""
    try:
        with open(_CACHE_PATH, "r", encoding="utf-8") as f:
            obj = json.load(f)
        return set(obj.get("emotes", [])), float(obj.get("ts", 0))
    except Exception:
        return set(), 0.0


def _save_cache(emotes: set):
    try:
        os.makedirs(os.path.dirname(_CACHE_PATH), exist_ok=True)
        with open(_CACHE_PATH, "w", encoding="utf-8") as f:
            json.dump({"ts": time.time(), "emotes": sorted(emotes)}, f)
    except Exception:
        pass


def _fetch_all_emotes(channels: list = None) -> set:
    all_sources = dict(_SOURCES_GLOBAL)
    all_sources.update(_build_channel_sources(channels or []))
    all_names = set()
    for key, url in all_sources.items():
        data = _fetch_json(url)
        if data is not None:
            found = _extract_emote_names(key, data)
            print(f"[TextFilter] {key}: {len(found)} emotes")
            all_names |= found
        else:
            print(f"[TextFilter] {key}: sin respuesta")
    return all_names


def _build_pattern(emotes: set):
    if not emotes:
        return None
    sorted_emotes = sorted(emotes, key=len, reverse=True)
    escaped = [re.escape(e) for e in sorted_emotes]
    return re.compile(r'(?<!\w)(' + '|'.join(escaped) + r')(?!\w)')


# -- EmoteRegistry: gestiona cache y actualizacion en background --------------

class EmoteRegistry:
    """Singleton que mantiene el conjunto de emotes actualizado en background."""

    def __init__(self, ttl_hours: float = 24.0, channels: list = None):
        self._ttl      = ttl_hours * 3600
        self._channels = channels or []
        self._lock     = threading.Lock()
        self._emotes: set = set()
        self._pattern = None
        self._initialized = threading.Event()
        self._start()

    def _start(self):
        cached, ts = _load_cache()
        if cached:
            self._update(cached | _SEED_EMOTES)
            print(f"[TextFilter] Cache cargada: {len(cached)} emotes")
            self._initialized.set()
            if time.time() - ts < self._ttl:
                return
        threading.Thread(target=self._refresh, daemon=True, name="emote-refresh").start()

    def _refresh(self):
        fresh = _fetch_all_emotes(self._channels)
        if fresh:
            combined = fresh | _SEED_EMOTES
            _save_cache(combined)
            self._update(combined)
            print(f"[TextFilter] Emotes actualizados: {len(combined)} total")
        elif not self._initialized.is_set():
            self._update(_SEED_EMOTES)
            print(f"[TextFilter] Sin red, usando semilla ({len(_SEED_EMOTES)} emotes)")
        self._initialized.set()

    def _update(self, emotes: set):
        pattern = _build_pattern(emotes)
        with self._lock:
            self._emotes = emotes
            self._pattern = pattern

    def add_extra(self, words: set):
        with self._lock:
            self._emotes |= words
            self._pattern = _build_pattern(self._emotes)

    def pattern(self):
        with self._lock:
            return self._pattern

    def count(self) -> int:
        with self._lock:
            return len(self._emotes)


_registry: Optional[EmoteRegistry] = None
_registry_lock = threading.Lock()


def _get_registry(ttl_hours: float = 24.0, channels: list = None) -> EmoteRegistry:
    global _registry
    with _registry_lock:
        if _registry is None:
            _registry = EmoteRegistry(ttl_hours, channels)
    return _registry


# -- TextFilter ----------------------------------------------------------------

class TextFilter:
    def __init__(self, config: dict):
        self.remove_unicode = config.get("remove_unicode_emoji", True)
        self.remove_twitch  = config.get("remove_twitch_emotes", True)
        self.remove_colon   = config.get("remove_colon_emotes", True)
        ttl                 = float(config.get("cache_ttl_hours", 24))
        extra               = set(config.get("extra_words", []))

        # Soporte para lista de canales y retrocompatibilidad con campo unico
        channels = config.get("twitch_channels", [])
        if not channels:
            # fallback a campos individuales de versiones anteriores
            cid  = config.get("twitch_channel_id", "")
            name = config.get("twitch_channel_name", "")
            if cid or name:
                channels = [{"id": cid, "name": name}]

        if self.remove_twitch:
            self._registry = _get_registry(ttl, channels)
            if extra:
                self._registry.add_extra(extra)
        else:
            self._registry = None

    def apply(self, text: str) -> str:
        if not text:
            return text
        if self.remove_unicode:
            text = _UNICODE_EMOJI_RE.sub(' ', text)
        if self.remove_colon:
            text = _COLON_EMOTE_RE.sub(' ', text)
        if self.remove_twitch and self._registry:
            pat = self._registry.pattern()
            if pat:
                text = pat.sub(' ', text)
        text = _MULTI_SPACE_RE.sub(' ', text).strip()
        return text

    def status(self) -> str:
        if self._registry:
            return f"{self._registry.count()} emotes cargados"
        return "filtrado de emotes desactivado"


# -- Singleton -----------------------------------------------------------------

_filter: Optional[TextFilter] = None


def get_text_filter() -> TextFilter:
    global _filter
    if _filter is None:
        try:
            from .app_config import get_app_config
            filter_config = get_app_config().get("text_filter", {})
        except Exception:
            filter_config = {}
        _filter = TextFilter(filter_config)
    return _filter


def reload_filter():
    global _filter, _registry
    _filter = None
    with _registry_lock:
        _registry = None


def filter_text(text: str) -> str:
    """Atajo: filtra el texto y devuelve la version limpia."""
    return get_text_filter().apply(text)