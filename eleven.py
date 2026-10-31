"""JARVIS: ElevenLabs awaaz (text-to-speech). Kivy ya main.py par depend nahi karta.

speaker = ElevenSpeaker(cache_dir)
speaker.speak(key, voice_id, text, on_error)   # thread me: mp3 banata hai, phir MediaPlayer se bajata hai
speaker.busy()   # bol raha hai ya awaaz ban rahi hai
speaker.stop()   # turant chup
Koi bhi galti ho to on_error(msg) bulaya jata hai (app phir phone ki apni awaaz se bol deta hai).
"""
import json
import os
import threading
import time

MODEL = "eleven_flash_v2_5"          # sabse tez; Hindi/Hinglish bhi bolta hai
API = "https://api.elevenlabs.io/v1/text-to-speech/"
MAX_CHARS = 700


class ElevenError(Exception):
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


def _error_message(code, body):
    low = (body or "").lower()
    if code == 401:
        return "ElevenLabs key galat hai"
    if code in (402, 403) or "payment" in low or "paid" in low:
        return "ElevenLabs: is voice/plan ke liye paid plan chahiye"
    if code == 404 or "voice_not_found" in low:
        return "ElevenLabs: Voice ID galat hai"
    if code == 429 or "quota" in low:
        return "ElevenLabs ka quota khatam / bahut requests"
    return "ElevenLabs error %s" % code


def build_request(key, voice_id, text):
    url = API + voice_id.strip() + "?output_format=mp3_44100_64"
    headers = {"xi-api-key": key.strip(), "Content-Type": "application/json",
               "Accept": "audio/mpeg"}
    body = json.dumps({"text": text, "model_id": MODEL}).encode("utf-8")
    return url, headers, body


def _download_java(url, headers, body, path):
    """Java helper (JarvisEleven.download) se: pyjnius me binary bytes padhna mushkil hai,
    isliye poora download Java me hota hai. (code, payload) lautata hai."""
    from jnius import autoclass
    Helper = autoclass("org.myassistant.myvoiceassistant.JarvisEleven")
    text = json.loads(body.decode("utf-8")).get("text", "")
    voice_id = url.split("/text-to-speech/")[1].split("?")[0]
    err = str(Helper.download(headers.get("xi-api-key", ""), voice_id, text, path) or "")
    if err:
        raise ElevenError(err)
    return 200, os.path.getsize(path) if os.path.exists(path) else 0


def _download_urllib(url, headers, body, path):
    import urllib.error
    import urllib.request
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=40) as resp:
            data = resp.read()
        with open(path, "wb") as fh:
            fh.write(data)
        return 200, len(data)
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", "replace")


def synthesize(key, voice_id, text, path, downloader=None):
    """Awaaz ki mp3 `path` par likho. Galti par ElevenError."""
    if not key or not key.strip():
        raise ElevenError("ElevenLabs key nahi hai")
    if not voice_id or not voice_id.strip():
        raise ElevenError("Voice ID nahi hai")
    text = trim_text(text)
    if not text:
        raise ElevenError("khali text")
    url, headers, body = build_request(key, voice_id, text)
    if downloader is None:
        try:
            import jnius  # noqa: F401
            downloader = _download_java
        except Exception:
            downloader = _download_urllib
    try:
        code, payload = downloader(url, headers, body, path)
    except ElevenError:
        raise
    except Exception as exc:
        raise ElevenError("ElevenLabs tak internet nahi pahunch paya (%s)" % str(exc)[:60])
    if code >= 400:
        raise ElevenError(_error_message(code, payload if isinstance(payload, str) else ""))
    if not os.path.exists(path) or os.path.getsize(path) < 200:
        raise ElevenError("ElevenLabs se awaaz nahi aayi")
    return path


class ElevenSpeaker:
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
            self._stop_flag["stop"] = True       # purani awaaz roko
            self._stop_flag = flag
            self._busy = True

        def work():
            path = os.path.join(self.cache_dir, "jarvis_eleven_%d.mp3" % gen)
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
                        print("eleven on_error failed:", exc2)
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
