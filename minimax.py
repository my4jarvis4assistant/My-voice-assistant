"""JARVIS: MiniMax awaaz (text-to-speech). Kivy ya main.py par depend nahi karta.

speaker = MiniMaxSpeaker(cache_dir)
speaker.speak(key, voice_id, text, on_error, on_done)   # thread me: mp3 banata hai, phir MediaPlayer se bajata hai
speaker.busy() / speaker.stop()
Koi bhi galti ho to on_error(msg) bulaya jata hai (app phir phone ki apni awaaz se bol deta hai).
"""
import json
import os
import threading
import time

API = "https://api.minimax.io/v1/t2a_v2"
MODELS = ("speech-2.8-turbo", "speech-2.6-turbo", "speech-02-turbo")
MAX_CHARS = 900


class MiniMaxError(Exception):
    pass


def trim_text(text, limit=MAX_CHARS):
    text = " ".join(str(text).split())
    if len(text) <= limit:
        return text
    cut = text[:limit]
    for sep in (". ", "? ", "! ", "। ", ", "):
        i = cut.rfind(sep)
        if i > limit * 0.5:
            return cut[:i + 1]
    return cut


def build_body(voice_id, text, model):
    return json.dumps({
        "model": model,
        "text": text,
        "stream": False,
        "language_boost": "auto",
        "voice_setting": {"voice_id": voice_id.strip(), "speed": 1.0, "vol": 1.0, "pitch": 0},
        "audio_setting": {"sample_rate": 32000, "bitrate": 128000, "format": "mp3", "channel": 1},
    }).encode("utf-8")


def _post_java(url, key, body):
    """(http_code, response_text). Java HttpURLConnection: phone par sabse bharosemand."""
    from jnius import autoclass, cast, jarray
    URL = autoclass("java.net.URL")
    BAOS = autoclass("java.io.ByteArrayOutputStream")
    conn = cast("java.net.HttpURLConnection", URL(url).openConnection())
    try:
        conn.setRequestMethod("POST")
        conn.setConnectTimeout(15000)
        conn.setReadTimeout(45000)
        conn.setRequestProperty("Authorization", "Bearer " + key.strip())
        conn.setRequestProperty("Content-Type", "application/json")
        conn.setDoOutput(True)
        out = conn.getOutputStream()
        out.write(body)
        out.flush()
        out.close()
        code = int(conn.getResponseCode())
        stream = conn.getErrorStream() if code >= 400 else conn.getInputStream()
        if stream is None:
            return code, ""
        baos = BAOS()
        buf = jarray("b")(16384)
        while True:
            n = stream.read(buf)
            if n < 0:
                break
            baos.write(buf, 0, n)
        stream.close()
        return code, bytes(bytearray([b & 0xFF for b in baos.toByteArray()])).decode("utf-8", "replace")
    finally:
        try:
            conn.disconnect()
        except Exception:
            pass


def _post_urllib(url, key, body):
    import urllib.error
    import urllib.request
    req = urllib.request.Request(url, data=body, method="POST", headers={
        "Authorization": "Bearer " + key.strip(), "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=45) as resp:
            return resp.getcode(), resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", "replace")


def _message(code, status, msg):
    low = (msg or "").lower()
    if code == 401 or status in (1004, 2049):
        return "MiniMax key galat hai"
    if status in (1008, 1039) or "balance" in low or "insufficient" in low:
        return "MiniMax me balance/credits khatam hain"
    if status == 1002 or code == 429:
        return "MiniMax: bahut requests, thodi der baad"
    if "voice" in low and ("not" in low or "exist" in low or "invalid" in low):
        return "MiniMax: Voice ID galat hai"
    if status == 2013 or status == 2049:
        return "MiniMax: request galat (%s)" % (msg or status)
    return "MiniMax error %s %s" % (status or code, (msg or "")[:50])


def synthesize(key, voice_id, text, path, poster=None):
    """Awaaz ki mp3 `path` par likho. Galti par MiniMaxError."""
    if not key or not key.strip():
        raise MiniMaxError("MiniMax key nahi hai")
    if not voice_id or not voice_id.strip():
        raise MiniMaxError("Voice ID nahi hai")
    text = trim_text(text)
    if not text:
        raise MiniMaxError("khali text")
    if poster is None:
        try:
            import jnius  # noqa: F401
            poster = _post_java
        except Exception:
            poster = _post_urllib
    last = "MiniMax se awaaz nahi aayi"
    for model in MODELS:
        try:
            code, resp = poster(API, key, build_body(voice_id, text, model))
        except Exception as exc:
            raise MiniMaxError("MiniMax tak internet nahi pahunch paya (%s)" % str(exc)[:60])
        try:
            data = json.loads(resp)
        except Exception:
            data = {}
        base = data.get("base_resp") or {}
        status = int(base.get("status_code", 0) or 0)
        smsg = str(base.get("status_msg", "") or "")
        audio = (data.get("data") or {}).get("audio") if isinstance(data.get("data"), dict) else None
        if code < 400 and status == 0 and audio:
            raw = bytes.fromhex(audio)
            if len(raw) < 200:
                raise MiniMaxError("MiniMax se awaaz nahi aayi")
            with open(path, "wb") as fh:
                fh.write(raw)
            return path
        last = _message(code, status, smsg)
        low = smsg.lower()
        if "model" in low or status == 2013:
            continue                               # agla model try karo
        break
    raise MiniMaxError(last)


def _android_play(path, flag):
    """MediaPlayer se bajao aur khatam hone tak ruko (ya flag['stop'] aane tak)."""
    from jnius import autoclass
    MediaPlayer = autoclass("android.media.MediaPlayer")
    mp = MediaPlayer()
    try:
        mp.setDataSource(path)
        mp.prepare()
        mp.start()
        started = time.time()
        while not flag["stop"]:
            time.sleep(0.1)
            if not mp.isPlaying() and time.time() - started > 0.4:
                break
            if time.time() - started > 120:
                break
    finally:
        try:
            mp.stop()
        except Exception:
            pass
        try:
            mp.release()
        except Exception:
            pass


class MiniMaxSpeaker:
    def __init__(self, cache_dir, synth=None, player=None):
        self.cache_dir = cache_dir
        self._synth = synth or synthesize
        self._player = player or _android_play
        self._gen = 0
        self._busy = False
        self._lock = threading.Lock()
        self._stop_flag = {"stop": False}

    def busy(self):
        return self._busy

    def stop(self):
        with self._lock:
            self._gen += 1
            self._stop_flag["stop"] = True
        self._busy = False

    def speak(self, key, voice_id, text, on_error=None, on_done=None):
        with self._lock:
            self._gen += 1
            gen = self._gen
            flag = {"stop": False}
            self._stop_flag["stop"] = True
            self._stop_flag = flag
            self._busy = True

        def work():
            path = os.path.join(self.cache_dir, "jarvis_minimax_%d.mp3" % gen)
            ok = False
            try:
                self._synth(key, voice_id, text, path)
                if gen == self._gen and not flag["stop"]:
                    self._player(path, flag)
                ok = True
            except Exception as exc:
                msg = str(exc) or exc.__class__.__name__
                if gen == self._gen and on_error is not None:
                    try:
                        on_error(msg)
                    except Exception as exc2:
                        print("minimax on_error failed:", exc2)
            finally:
                try:
                    os.remove(path)
                except Exception:
                    pass
                if gen == self._gen:
                    self._busy = False
                    if ok and on_done is not None and not flag["stop"]:
                        try:
                            on_done()
                        except Exception:
                            pass

        threading.Thread(target=work, daemon=True).start()
