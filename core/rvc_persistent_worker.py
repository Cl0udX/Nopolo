"""
Persistent RVC worker subprocess.

Instead of spawning a new process for every conversion (which reloads Hubert
200 MB + PyTorch + fairseq each time → 3–4 s overhead), this module keeps ONE
subprocess alive across calls.  The subprocess loads Hubert once on startup and
caches the currently loaded RVC voice model.  Each call only pays the cost of
the actual conversion (~1–2 s on CUDA with FCPE).

After MAX_REQUESTS conversions the worker is transparently restarted to avoid
CUDA memory drift.
"""

import multiprocessing as mp
import numpy as np
import os
import sys
import threading

MAX_REQUESTS = 50   # Restart worker after this many conversions


# ─────────────────────────────────────────────────────────────────────────────
# Worker main function  (runs inside the subprocess)
# ─────────────────────────────────────────────────────────────────────────────

def _worker_main(request_q: mp.Queue, result_q: mp.Queue, base_dir: str):
    """Entry point for the persistent worker subprocess."""

    # Fix stdout encoding on Windows
    if sys.platform == 'win32':
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')

    import traceback
    import gc

    # ── Setup paths ───────────────────────────────────────────────────────────
    sys.path.insert(0, base_dir)
    sys.path.insert(0, os.path.join(base_dir, 'rvc'))

    os.environ['index_root']  = os.path.join(base_dir, 'voices')
    os.environ['weight_root'] = os.path.join(base_dir, 'voices')
    os.environ['hubert_path'] = os.path.join(base_dir, 'models', 'hubert_base.pt')
    os.environ['rmvpe_root']  = os.path.join(base_dir, 'models')

    def log(msg):
        print(f"[PersistentRVC] {msg}", flush=True)

    # ── Import heavy libs once ────────────────────────────────────────────────
    try:
        import torch
        import platform
        from rvc.modules.vc.modules import VC
        log("Imports OK")
    except Exception as e:
        result_q.put({'error': f'import failed: {e}'})
        return

    # ── Instantiate VC (this also implicitly loads Hubert on first call) ──────
    try:
        vc = VC()
        log("VC created")
    except Exception as e:
        result_q.put({'error': f'VC() failed: {e}'})
        return

    # Decide F0 method once
    if platform.system() == 'Darwin':
        f0_method = 'pm'
    elif torch.cuda.is_available():
        f0_method = 'fcpe'
    else:
        f0_method = 'rmvpe'
    log(f"F0 method: {f0_method}")

    loaded_model_path = None   # currently loaded RVC model

    # ── Multi-model LRU cache ─────────────────────────────────────────────────
    # Keeps up to MODEL_CACHE_SIZE voice models warm in VRAM.
    # Switching between cached models costs only a few pointer swaps (~0ms)
    # instead of a full disk load + GPU transfer (~0.5–1s).
    from collections import OrderedDict
    MODEL_CACHE_SIZE = 5
    model_cache = OrderedDict()   # model_path → {net_g, tgt_sr, if_f0, version, cpt, pipeline, n_spk}

    def _cache_save(path):
        """Snapshot current vc state into the cache."""
        model_cache[path] = {
            'net_g':    vc.net_g,
            'tgt_sr':   vc.tgt_sr,
            'if_f0':    vc.if_f0,
            'version':  vc.version,
            'cpt':      vc.cpt,
            'pipeline': vc.pipeline,
            'n_spk':    vc.n_spk,
        }
        model_cache.move_to_end(path)
        # Evict LRU entry when over capacity
        while len(model_cache) > MODEL_CACHE_SIZE:
            evicted_path, evicted = model_cache.popitem(last=False)
            try:
                evicted['net_g'].cpu()
                del evicted['net_g']
            except Exception:
                pass
            log(f"Cache evicted: {os.path.basename(evicted_path)}")

    def _cache_restore(path):
        """Restore vc state from cache. Returns True on hit."""
        if path not in model_cache:
            return False
        model_cache.move_to_end(path)
        s = model_cache[path]
        vc.net_g    = s['net_g']
        vc.tgt_sr   = s['tgt_sr']
        vc.if_f0    = s['if_f0']
        vc.version  = s['version']
        vc.cpt      = s['cpt']
        vc.pipeline = s['pipeline']
        vc.n_spk    = s['n_spk']
        return True

    # ── Signal to parent that we are ready ────────────────────────────────────
    result_q.put({'ready': True})
    log(f"Ready (model cache size: {MODEL_CACHE_SIZE})")

    # ── Main loop ────────────────────────────────────────────────────────────
    while True:
        try:
            request = request_q.get(timeout=60)
        except Exception:
            # Queue.Empty after timeout — just loop and wait
            continue

        if request is None:
            log("Shutdown signal received")
            break

        try:
            model_path  = request['model_path']
            index_path  = request.get('index_path')
            input_wav   = request['input_wav']
            pitch_shift = request['pitch_shift']
            index_rate  = request['index_rate']
            filter_rad  = request['filter_radius']
            rms_mix     = request['rms_mix_rate']
            protect     = request['protect']

            # Load / switch voice model — check cache first
            if loaded_model_path != model_path:
                if _cache_restore(model_path):
                    log(f"Cache HIT: {os.path.basename(model_path)}")
                else:
                    log(f"Loading model: {os.path.basename(model_path)}")
                    vc.get_vc(model_path)
                    _cache_save(model_path)
                    log("Model loaded and cached")
                loaded_model_path = model_path

            # Validate index path
            if index_path and not os.path.exists(index_path):
                log(f"Index not found, ignoring: {index_path}")
                index_path = None

            # Run conversion
            tgt_sr, audio_opt, times, _ = vc.vc_inference(
                sid=1,
                input_audio_path=input_wav,
                f0_up_key=pitch_shift,
                f0_method=f0_method,
                f0_file=None,
                index_file=index_path,
                index_rate=index_rate,
                filter_radius=filter_rad,
                rms_mix_rate=rms_mix,
                protect=protect,
            )

            if audio_opt is None or tgt_sr is None:
                raise RuntimeError("vc_inference returned None")

            # Convert to float32 and send as raw bytes (fast, no pickle overhead)
            audio_f32 = audio_opt.astype(np.float32) / 32768.0
            result_q.put({
                'audio_bytes': audio_f32.tobytes(),
                'sample_rate': int(tgt_sr),
            })

            # Light CUDA cleanup
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            gc.collect()

        except Exception as e:
            log(f"Conversion error: {e}")
            traceback.print_exc()
            result_q.put({'error': str(e)})


# ─────────────────────────────────────────────────────────────────────────────
# PersistentRVCEngine — drop-in replacement for RVCIsolatedEngine
# ─────────────────────────────────────────────────────────────────────────────

class PersistentRVCEngine:
    """
    Drop-in replacement for RVCIsolatedEngine.

    Keeps a single long-lived worker subprocess alive so that Hubert and
    the current voice model stay in VRAM / RAM between conversions.

    First conversion is still ~2–3 s (process startup + Hubert load).
    Subsequent conversions of the SAME voice: ~1–2 s (just inference).
    Voice switches: ~1 s extra to load the new RVC model.
    """

    def __init__(self, max_requests: int = MAX_REQUESTS):
        self._max_requests  = max_requests
        self._process       = None
        self._request_q     = None
        self._result_q      = None
        self._req_count      = 0
        self._lock          = threading.Lock()
        self._base_dir      = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        # Config
        self.config         = None
        self.model_loaded   = False

    # ── Public API (mirrors RVCIsolatedEngine) ────────────────────────────────

    def load_model(self, config):
        """Store config — actual model loading happens in the worker."""
        self.config       = config
        self.model_loaded = True
        print(f"[PersistentRVC] Config stored: {config.name}")

    def convert(self, input_wav_path: str):
        """
        Convert audio using the persistent worker.

        Returns (audio_np_float32, sample_rate)
        """
        if not self.model_loaded or self.config is None:
            raise RuntimeError("No RVC config loaded. Call load_model() first.")

        with self._lock:
            self._ensure_worker_running()

            request = {
                'model_path':    self.config.model_path,
                'index_path':    self.config.index_path,
                'input_wav':     input_wav_path,
                'pitch_shift':   self.config.pitch_shift,
                'index_rate':    self.config.index_rate,
                'filter_radius': self.config.filter_radius,
                'rms_mix_rate':  self.config.rms_mix_rate,
                'protect':       self.config.protect,
            }
            self._request_q.put(request)

            result = self._result_q.get(timeout=120)

            if 'error' in result:
                raise RuntimeError(f"Worker error: {result['error']}")

            audio = np.frombuffer(result['audio_bytes'], dtype=np.float32).copy()
            sr    = result['sample_rate']

            self._req_count += 1
            if self._req_count >= self._max_requests:
                print(f"[PersistentRVC] {self._req_count} conversions done — "
                      f"restarting worker to free memory")
                self._stop_worker()   # Next call will restart transparently

            return audio, sr

    def emergency_cleanup(self):
        """Stop the worker process."""
        self._stop_worker()

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _ensure_worker_running(self):
        if self._process is not None and self._process.is_alive():
            return
        self._start_worker()

    def _start_worker(self):
        print("[PersistentRVC] Starting worker subprocess…")
        ctx = mp.get_context('spawn')
        self._request_q = ctx.Queue()
        self._result_q  = ctx.Queue()
        self._process   = ctx.Process(
            target=_worker_main,
            args=(self._request_q, self._result_q, self._base_dir),
            daemon=True,
        )
        self._process.start()
        self._req_count = 0

        # Wait for ready signal (or error)
        try:
            msg = self._result_q.get(timeout=120)
            if 'error' in msg:
                raise RuntimeError(f"Worker failed to start: {msg['error']}")
            print("[PersistentRVC] Worker ready")
        except Exception as e:
            self._process.terminate()
            self._process = None
            raise RuntimeError(f"Worker did not become ready: {e}")

    def _stop_worker(self):
        if self._process and self._process.is_alive():
            try:
                self._request_q.put(None)   # shutdown signal
                self._process.join(timeout=5)
            except Exception:
                pass
            if self._process.is_alive():
                self._process.terminate()
        self._process   = None
        self._request_q = None
        self._result_q  = None
        self._req_count  = 0


# ── Module-level singleton ─────────────────────────────────────────────────────
_persistent_engine: "PersistentRVCEngine | None" = None
_singleton_lock = threading.Lock()


def get_persistent_rvc_engine() -> PersistentRVCEngine:
    """Return the shared PersistentRVCEngine singleton."""
    global _persistent_engine
    if _persistent_engine is None:
        with _singleton_lock:
            if _persistent_engine is None:
                _persistent_engine = PersistentRVCEngine()
    return _persistent_engine
