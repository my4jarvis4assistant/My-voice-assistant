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
    if "missing_permissions" in low:
        return ("ElevenLabs key me permission kam hai. ElevenLabs me key edit karke "
                "'Text to Speech' aur 'Voices: Read' On kijiye")
    if code == 401:
        return "ElevenLabs key galat hai (poori key, bina space ke, dobara paste kijiye)"
    if code in (402, 403) or "payment" in low or "paid" in low:
        return "ElevenLabs: is voice/plan ke liye paid plan chahiye"
    if code == 404 or "voice_not_found" in low:
        return "ElevenLabs: Voice ID galat hai"
    if code == 429 or "quota" in low:
        return "ElevenLabs ka quota khatam / bahut requests"
    return "ElevenLabs error %s" % code


def build_request(key, voice_id, text, lang=None):
    url = API + voice_id.strip() + "?output_format=mp3_44100_64"
    headers = {"xi-api-key": key.strip(), "Content-Type": "application/json",
               "Accept": "audio/mpeg"}
    payload = {"text": text, "model_id": MODEL}
    if lang:
        payload["language_code"] = lang          # "hi": Hindi ke hisaab se bolo (Indian lehja)
    body = json.dumps(payload).encode("utf-8")
    return url, headers, body


# ---------------------------------------------------------------- Hindi (Devanagari) ----
_HINDI_CACHE = {}
GEMINI = "https://generativelanguage.googleapis.com/v1beta/models/%s:generateContent"
HINDI_SYSTEM = ("Tum Hinglish (Roman me likhi Hindi) ko Devanagari Hindi me badalte ho taaki text-to-speech "
                "asli Indian Hindi jaisa bole. Matlab aur shabd bilkul na badlo, sirf lipi badlo. "
                "English shabd (WhatsApp, message, call, Instagram, naam) Devanagari me likho (jaise व्हाट्सएप, मैसेज). "
                "Naam ko Devanagari me likho. Sankhya/time jaise 5 baje ko '5 बजे' likho. "
                "Agar poora text sirf English sentence hai to use bilkul waisa hi lautao. "
                "Sirf badla hua text do, koi samjhaish ya quote nahi.")


def has_devanagari(text):
    return any("\u0900" <= ch <= "\u097f" for ch in str(text))


def to_hindi(gemini_key, text, requester=None, timeout_models=("gemini-2.5-flash-lite", "gemini-2.5-flash")):
    """(text, lang): Hinglish ko Devanagari me badalkar ("hi"). Kuch bhi gadbad ho to (text, None) = jaisa tha waisa."""
    text = " ".join(str(text).split())
    if not gemini_key or not gemini_key.strip() or not text:
        return text, None
    if has_devanagari(text):
        return text, "hi"
    if text in _HINDI_CACHE:
        return _HINDI_CACHE[text]
    if requester is None:
        try:
            import jnius  # noqa: F401
            requester = _java_request
        except Exception:
            requester = _urllib_request
    body = json.dumps({
        "systemInstruction": {"parts": [{"text": HINDI_SYSTEM}]},
        "contents": [{"role": "user", "parts": [{"text": text}]}],
        "generationConfig": {"temperature": 0.2, "maxOutputTokens": 700,
                             "thinkingConfig": {"thinkingBudget": 0}},
    }).encode("utf-8")
    for model in timeout_models:
        try:
            headers = {"x-goog-api-key": gemini_key.strip(), "Content-Type": "application/json"}
            code, data = requester("POST", GEMINI % model, headers, body)
            raw = data.decode("utf-8", "replace") if isinstance(data, bytes) else str(data)
            if code != 200:
                continue
            parts = json.loads(raw)["candidates"][0]["content"]["parts"]
            out = "".join(p.get("text", "") for p in parts).strip()
            if out:
                res = (out, "hi" if has_devanagari(out) else None)
                if len(_HINDI_CACHE) > 200:
                    _HINDI_CACHE.clear()
                _HINDI_CACHE[text] = res
                return res
        except Exception:
            continue
    return text, None


def _read_all(stream, charset):
    """Java stream ko poora padhkar python str me lautao (java.util.Scanner, koi byte-array nahi chahiye)."""
    from jnius import autoclass
    Scanner = autoclass("java.util.Scanner")
    sc = Scanner(stream, charset).useDelimiter("\\A")
    try:
        return str(sc.next()) if sc.hasNext() else ""
    finally:
        sc.close()


def _java_request(method, url, headers, body, binary=False):
    """Java HttpURLConnection se: (code, data_bytes). pyjnius me byte-array nahi bana sakte, isliye
    awaaz ko Base64InputStream se text bana kar padhte hain (Scanner), phir Python me decode karte hain.
    Koi apni Java class nahi chahiye (background thread me app ki class milti nahi)."""
    import base64
    from jnius import autoclass, cast
    URL = autoclass("java.net.URL")
    Scanner = autoclass("java.util.Scanner")
    Base64 = autoclass("android.util.Base64")
    B64Stream = autoclass("android.util.Base64InputStream")
    conn = cast("java.net.HttpURLConnection", URL(url).openConnection())
    try:
        conn.setRequestMethod(method)
        conn.setConnectTimeout(15000)
        conn.setReadTimeout(40000)
        for k, v in headers.items():
            conn.setRequestProperty(k, v)
        if body is not None:
            conn.setDoOutput(True)
            out = conn.getOutputStream()
            out.write(body)
            out.flush()
            out.close()
        code = int(conn.getResponseCode())
        if code >= 400:
            err = conn.getErrorStream()
            text = ""
            if err is not None:
                err = cast("java.io.InputStream", err)      # pyjnius ko saaf type chahiye
                sc = Scanner(err, "UTF-8")
                sc.useDelimiter("\\A")
                text = str(sc.next()) if sc.hasNext() else ""
                err.close()
            return code, text.encode("utf-8")
        stream = cast("java.io.InputStream", conn.getInputStream())
        if not binary:                                        # JSON/text jawab: seedha padho
            sc = Scanner(stream, "UTF-8")
            sc.useDelimiter("\\A")
            text = str(sc.next()) if sc.hasNext() else ""
            stream.close()
            return code, text.encode("utf-8")
        b64 = cast("java.io.InputStream", B64Stream(stream, Base64.NO_WRAP))
        sc = Scanner(b64, "US-ASCII")
        sc.useDelimiter("\\A")
        text = str(sc.next()) if sc.hasNext() else ""
        stream.close()
        return code, base64.b64decode(text)
    finally:
        try:
            conn.disconnect()
        except Exception:
            pass


def _download_java(url, headers, body, path):
    code, data = _java_request("POST", url, headers, body, binary=True)
    if code >= 400:
        return code, data.decode("utf-8", "replace")
    with open(path, "wb") as fh:
        fh.write(data)
    return code, len(data)


def _premade_full(key, requester=None):
    """Account ki 'premade' awaazein, poori jaankari ke saath (naam, voice_id, labels)."""
    if not key or not key.strip():
        raise ElevenError("ElevenLabs key nahi hai")
    headers = {"xi-api-key": key.strip(), "Accept": "application/json"}
    url = "https://api.elevenlabs.io/v1/voices"
    if requester is None:
        try:
            import jnius  # noqa: F401
            requester = _java_request
        except Exception:
            requester = _urllib_request
    try:
        code, data = requester("GET", url, headers, None)
    except Exception as exc:
        raise ElevenError("ElevenLabs tak internet nahi pahunch paya (%s)" % str(exc)[:60])
    text = data.decode("utf-8", "replace") if isinstance(data, bytes) else str(data)
    if code >= 400:
        raise ElevenError(_error_message(code, text))
    try:
        voices = json.loads(text).get("voices", [])
    except Exception:
        raise ElevenError("ElevenLabs ka jawab samajh nahi aaya")
    out = []
    for v in voices:
        if str(v.get("category", "")).lower() != "premade":
            continue
        name = str(v.get("name", "")).split(" - ")[0].strip()
        vid = str(v.get("voice_id", "")).strip()
        if name and vid:
            out.append((name, vid, v.get("labels") or {}))
    return out


def list_free_voices(key, limit=7, requester=None):
    """Account ki 'premade' (free plan par chalne wali) awaazein: [(naam, voice_id)]."""
    return [(n, v) for n, v, _l in _premade_full(key, requester)][:limit]


MALE_PREF = ("Brian", "Roger", "George", "Daniel", "Eric", "Chris", "Callum", "Charlie", "Will", "Bill", "Liam")
FEMALE_PREF = ("Sarah", "Laura", "Alice", "Matilda", "Jessica", "Lily")


def pick_hindi_voices(key, requester=None):
    """((naam, id) Male, (naam, id) Female) - free (premade) awaazon me se Hindi ke liye achhe."""
    full = _premade_full(key, requester)

    def pick(prefs, gender):
        by = {n.lower(): (n, v) for n, v, _l in full}
        for p in prefs:
            if p.lower() in by:
                return by[p.lower()]
        for n, v, lab in full:
            if str(lab.get("gender", "")).lower() == gender:
                return (n, v)
        return None

    return pick(MALE_PREF, "male"), pick(FEMALE_PREF, "female")


def _urllib_request(method, url, headers, body):
    import urllib.error
    import urllib.request
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=40) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read()


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


def synthesize(key, voice_id, text, path, downloader=None, lang=None):
    """Awaaz ki mp3 `path` par likho. Galti par ElevenError."""
    if not key or not key.strip():
        raise ElevenError("ElevenLabs key nahi hai")
    if not voice_id or not voice_id.strip():
        raise ElevenError("Voice ID nahi hai")
    text = trim_text(text)
    if not text:
        raise ElevenError("khali text")
    url, headers, body = build_request(key, voice_id, text, lang)
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

    def speak(self, key, voice_id, text, on_error=None, on_done=None, hindi_key=None):
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
                lang = None
                say = text
                if hindi_key:
                    say, lang = to_hindi(hindi_key, text)       # Hinglish -> Devanagari: Indian lehja
                if lang:
                    self._synth(key, voice_id, say, path, lang=lang)
                else:
                    self._synth(key, voice_id, say, path)
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
