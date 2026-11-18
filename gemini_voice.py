"""JARVIS: Gemini awaaz (free tier). Aapki Gemini key se hi chalti hai, alag account/paise nahi.

speaker = minimax.MiniMaxSpeaker(cache_dir, synth=gemini_voice.synthesize, prefix="jarvis_gemini_")
synthesize(keys, voice_name, text, path): keys me kai keys ho sakti hain (jo AIza se shuru hon wahi chalti hain).
Gemini PCM deta hai; yahan usse WAV banakar `path` par likhte hain.
"""
import base64
import json
import re
import struct

MODELS = ("gemini-3.1-flash-tts-preview", "gemini-2.5-flash-preview-tts")
URL = "https://generativelanguage.googleapis.com/v1beta/models/%s:generateContent"
MAX_CHARS = 700
STYLE = "Say in a calm, natural, clear Indian accent: "

# (dikhne wala naam, Gemini voice, andaaz)
VOICES = [("Gemini Charon", "Charon"), ("Gemini Orus", "Orus"), ("Gemini Iapetus", "Iapetus"),
          ("Gemini Puck", "Puck"), ("Gemini Fenrir", "Fenrir"), ("Gemini Algenib", "Algenib"),
          ("Gemini Umbriel", "Umbriel"), ("Gemini Achird", "Achird")]


class GeminiVoiceError(Exception):
    pass


def gemini_keys(raw):
    out = []
    for k in re.split(r"[\s,;]+", str(raw or "")):
        k = k.strip()
        if k.startswith("AIza") and k not in out:
            out.append(k)
    return out


def voice_of(display_name):
    for name, v in VOICES:
        if name == display_name:
            return v
    return ""


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


def build_body(voice, text):
    return json.dumps({
        "contents": [{"parts": [{"text": STYLE + text}]}],
        "generationConfig": {
            "responseModalities": ["AUDIO"],
            "speechConfig": {"voiceConfig": {"prebuiltVoiceConfig": {"voiceName": voice}}},
        },
    }).encode("utf-8")


def wav_bytes(pcm, rate=24000):
    return (b"RIFF" + struct.pack("<I", 36 + len(pcm)) + b"WAVEfmt " +
            struct.pack("<IHHIIHH", 16, 1, 1, rate, rate * 2, 2, 16) + b"data" +
            struct.pack("<I", len(pcm)) + pcm)


def _post_java(url, key, body):
    from jnius import autoclass, cast
    URL_ = autoclass("java.net.URL")
    Writer = autoclass("java.io.OutputStreamWriter")
    Reader = autoclass("java.io.InputStreamReader")
    Buffered = autoclass("java.io.BufferedReader")
    conn = cast("java.net.HttpURLConnection", URL_(url).openConnection())
    try:
        conn.setRequestMethod("POST")
        conn.setConnectTimeout(15000)
        conn.setReadTimeout(60000)
        conn.setRequestProperty("x-goog-api-key", key)
        conn.setRequestProperty("Content-Type", "application/json")
        conn.setDoOutput(True)
        w = Writer(conn.getOutputStream(), "UTF-8")
        w.write(body.decode("utf-8"))
        w.flush()
        w.close()
        code = int(conn.getResponseCode())
        stream = conn.getErrorStream() if code >= 400 else conn.getInputStream()
        if stream is None:
            return code, ""
        rd = Buffered(Reader(stream, "UTF-8"))
        parts = []
        while True:
            line = rd.readLine()
            if line is None:
                break
            parts.append(str(line))
        rd.close()
        return code, "".join(parts)
    finally:
        try:
            conn.disconnect()
        except Exception:
            pass


def _post_urllib(url, key, body):
    import urllib.error
    import urllib.request
    req = urllib.request.Request(url, data=body, method="POST",
                                 headers={"x-goog-api-key": key, "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return resp.getcode(), resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", "replace")


def _post_auto(url, key, body):
    try:
        import jnius  # noqa: F401
    except Exception:
        return _post_urllib(url, key, body)
    try:
        return _post_java(url, key, body)
    except Exception as exc:
        print("gemini voice java post failed, urllib try:", exc)
        return _post_urllib(url, key, body)


def _extract(resp):
    """(pcm_bytes, rate) ya (None, 0)."""
    try:
        data = json.loads(resp)
        for part in data["candidates"][0]["content"]["parts"]:
            inl = part.get("inlineData") or part.get("inline_data")
            if inl and inl.get("data"):
                mime = str(inl.get("mimeType") or inl.get("mime_type") or "")
                m = re.search(r"rate=(\d+)", mime)
                return base64.b64decode(inl["data"]), int(m.group(1)) if m else 24000
    except Exception:
        pass
    return None, 0


def synthesize(keys, voice_name, text, path, poster=None):
    """voice_name: 'Charon' jaisa Gemini naam (ya 'Gemini Charon')."""
    ks = gemini_keys(keys)
    if not ks:
        raise GeminiVoiceError("Gemini key nahi hai (AIza se shuru hone wali key chahiye)")
    voice = voice_of(voice_name) or str(voice_name).replace("Gemini ", "").strip()
    if not voice:
        raise GeminiVoiceError("Voice nahi chuni")
    text = trim_text(text)
    if not text:
        raise GeminiVoiceError("khali text")
    poster = poster or _post_auto
    body = build_body(voice, text)
    last = "Gemini se awaaz nahi aayi"
    limited = False
    for model in MODELS:
        for key in ks:
            for _try in range(2):                       # kabhi kabhi pehli baar khali aata hai
                try:
                    code, resp = poster(URL % model, key, body)
                except Exception as exc:
                    raise GeminiVoiceError("Gemini tak internet nahi pahunch paya (%s)" % str(exc)[:60])
                if code < 400:
                    pcm, rate = _extract(resp)
                    if pcm and len(pcm) > 400:
                        with open(path, "wb") as fh:
                            fh.write(wav_bytes(pcm, rate))
                        return path
                    last = "Gemini ne awaaz khali bheji"
                    continue
                if code == 429:
                    limited = True
                    last = "Gemini awaaz ki free limit khatam (kal ya thodi der baad)"
                elif code in (400, 403) and "api key" in resp.lower():
                    last = "Gemini key galat hai"
                elif code == 404:
                    last = "Gemini awaaz model nahi mila"
                else:
                    last = "Gemini awaaz error %s" % code
                break
    if limited:
        last = "Gemini awaaz ki free limit khatam (kal ya thodi der baad)"
    raise GeminiVoiceError(last)
