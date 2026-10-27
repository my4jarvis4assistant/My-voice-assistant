"""JARVIS AI brain - Gemini se baat-cheet.

Is file me Kivy ka koi import nahi hai, isliye isko alag se test kiya ja sakta hai.
Android par network ka kaam Java ke HttpURLConnection (pyjnius) se hota hai, jo phone ke
apne certificates use karta hai (isliye python me openssl jodne ki zaroorat nahi).
Computer par (test ke liye) normal urllib chalta hai.

Use:
    client = GeminiClient(get_key=lambda: "AIza...", get_verbosity=lambda: "Balanced")
    ok, text = client.ask("EPS kya hota hai?")        # background thread me chalaiye
"""
import json
import re
import time
import urllib.error
import urllib.request

BASE_URL = "https://generativelanguage.googleapis.com/v1beta"

# Model naam badalte rehte hain, isliye list me se apne aap chunte hain (is order me).
PREFERRED = ("gemini-3-flash", "gemini-2.5-flash", "gemini-2.0-flash")
BAD_TOKENS = ("lite", "image", "tts", "live", "audio", "embedding", "vision", "robotics",
              "computer", "learnlm", "gemma", "thinking", "exp", "native", "dialog",
              "aqa", "imagen", "veo")

CONNECT_TIMEOUT = 15
READ_TIMEOUT = 45
MAX_TURNS = 8                 # kitni pichhli baatein yaad rakhni hain
MAX_HISTORY_CHARS = 7000

MESSAGES = {   # Hinglish error messages (bolne ke liye bhi theek)
    "nokey": "Gemini API key set nahi hai. Settings me jaakar key daaliye.",
    "badkey": "Gemini API key sahi nahi lag rahi. Settings me key dobara check kijiye.",
    "forbidden": "Gemini ne is key ko allow nahi kiya. Key ya uski permission check kijiye.",
    "quota": "Abhi Gemini ki free limit poori ho gayi hai. Thodi der baad dobara poochiye.",
    "nomodel": "Gemini ka koi model abhi available nahi mila. Thodi der baad try kijiye.",
    "perm": ("App ko internet ki permission nahi mili. buildozer.spec me "
             "android.permission.INTERNET jodkar APK dobara build kijiye."),
    "network": "Internet nahi chal raha lagta hai. Connection check karke dobara boliye.",
    "server": "Gemini server abhi busy hai. Thodi der baad dobara try kijiye.",
    "blocked": "Is sawal ka jawab main nahi de sakta. Kuch aur poochiye.",
    "empty": "Gemini se jawab nahi mil paya. Dobara poochiye.",
    "other": "AI se baat karte waqt kuch gadbad ho gayi. Dobara try kijiye.",
}


class AIError(Exception):
    def __init__(self, kind, detail=""):
        super().__init__(kind)
        self.kind = kind
        self.detail = detail

    @property
    def message(self):
        return MESSAGES.get(self.kind, MESSAGES["other"])


# ------------------------------------------------------------------ HTTP ----
def _read_java_stream(stream, BufferedReader, InputStreamReader):
    if stream is None:
        return ""
    reader = BufferedReader(InputStreamReader(stream, "UTF-8"))
    lines = []
    while True:
        line = reader.readLine()
        if line is None:
            break
        lines.append(str(line))
    reader.close()
    return "\n".join(lines)


def _http_java(method, url, headers, body, timeout):
    from jnius import autoclass
    URL = autoclass("java.net.URL")
    BufferedReader = autoclass("java.io.BufferedReader")
    InputStreamReader = autoclass("java.io.InputStreamReader")
    conn = URL(url).openConnection()
    try:
        conn.setRequestMethod(method)
        conn.setConnectTimeout(int(timeout[0] * 1000))
        conn.setReadTimeout(int(timeout[1] * 1000))
        for key, value in headers.items():
            conn.setRequestProperty(key, value)
        if body is not None:
            conn.setDoOutput(True)
            out = conn.getOutputStream()
            out.write(body)
            out.flush()
            out.close()
        code = int(conn.getResponseCode())
        stream = conn.getInputStream() if code < 400 else conn.getErrorStream()
        return code, _read_java_stream(stream, BufferedReader, InputStreamReader)
    finally:
        try:
            conn.disconnect()
        except Exception:
            pass


def _http_urllib(method, url, headers, body, timeout):
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout[1]) as resp:
            return resp.status, resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", "replace")


_PERM_WORDS = ("Permission denied", "INTERNET", "SecurityException")
_NET_WORDS = ("UnknownHost", "ConnectException", "SocketTimeout", "SSLHandshake",
              "NoRouteToHost", "UnknownService", "Network is unreachable", "timed out")


def http_request(method, url, headers, body=None, timeout=(CONNECT_TIMEOUT, READ_TIMEOUT)):
    """(status_code, text). Network band ho to AIError('network')."""
    try:
        import jnius  # noqa: F401  (sirf Android par hota hai)
        have_java = True
    except Exception:
        have_java = False
    java_err = ""
    if have_java:
        try:
            return _http_java(method, url, headers, body, timeout)
        except Exception as exc:                       # JavaException ya python error
            java_err = (repr(exc) + " " + str(exc)).strip()
            print("JARVIS AI: Java HTTP fail:", java_err[:300])
            if any(w in java_err for w in _PERM_WORDS):
                raise AIError("perm", java_err)
            if any(w in java_err for w in _NET_WORDS):
                raise AIError("network", java_err)
    try:
        return _http_urllib(method, url, headers, body, timeout)
    except Exception as exc:
        py_err = repr(exc)
        detail = ("java: " + java_err[:160] + " | ") if java_err else ""
        detail += "py: " + py_err[:160]
        if any(w in detail for w in _PERM_WORDS):
            raise AIError("perm", detail)
        raise AIError("network", detail)


# ---------------------------------------------------------------- MODELS ----
def rank_models(names):
    """generateContent wale model naamon me se behtareen order banao."""
    names = [n.split("/", 1)[-1] for n in names]
    good = [n for n in names if not any(b in n for b in BAD_TOKENS)]
    ordered = []
    for pref in PREFERRED:
        matches = [n for n in good if n == pref or n.startswith(pref + "-")]
        # exact naam pehle, phir 'latest', phir sabse chhota naam
        matches.sort(key=lambda n: (n != pref, not n.endswith("latest"), len(n), n))
        for n in matches:
            if n not in ordered:
                ordered.append(n)
    others = sorted((n for n in good if "flash" in n and n not in ordered),
                    key=lambda n: (len(n), n))
    ordered += others
    return ordered


# ---------------------------------------------------------------- PROMPT ----
LENGTH_RULES = {
    "Concise": "Jawab bahut chhota rakho: ek ya do chhote vaakya.",
    "Balanced": "Jawab chhota rakho: do se chaar vaakya, jab tak user detail na maange.",
    "Detailed": ("Jawab detail me do, step by step samjhao, par 150 shabd se zyada nahi "
                 "(jab tak user aur lamba na maange)."),
}


def system_prompt(verbosity="Balanced", now=None):
    now = now or time.strftime("%A, %d %B %Y, %I:%M %p")
    rule = LENGTH_RULES.get(verbosity, LENGTH_RULES["Balanced"])
    return (
        "Tum JARVIS ho, user ke phone par chalne wala personal voice assistant. "
        "User se ek samajhdar dost ki tarah, natural Hinglish me baat karo: Hindi shabd "
        "Roman (English) letters me likho aur beech beech me English words use kar sakte ho. "
        "Tumhara jawab bolkar sunaya jayega, isliye markdown, bullet points, emoji, symbols, "
        "table aur web link bilkul mat likho; seedhe saaf vaakyon me bolo. "
        "Formula ya calculation ho to use shabdon me bolo (jaise 'EPS barabar net profit "
        "divided by shares'). " + rule + " "
        "Commerce, accounts, economics, maths ya science ke sawal ho to dhyan se step by step "
        "solve karo, calculation dobara check karo aur final answer saaf bolo. "
        "Agar jawab pata nahi ya pakka nahi ho to seedha bol do, andaza mat lagao. "
        "Live ya aaj ki khabar, price jaisi cheezein tumhare paas nahi hain, unhe mat banao. "
        "Pichhli baat-cheet ka context yaad rakho. "
        "Abhi ka samay: " + now + "."
    )


_EMOJI = re.compile("[\U0001F000-\U0001FAFF☀-➿️‍]")


def clean_reply(text):
    """Markdown/emoji hatao taaki screen par aur bolne me saaf rahe."""
    t = str(text or "")
    t = _EMOJI.sub("", t)
    t = re.sub(r"```.*?```", " ", t, flags=re.S)
    t = t.replace("**", "").replace("__", "").replace("`", "")
    t = re.sub(r"^\s{0,3}#{1,6}\s*", "", t, flags=re.M)
    t = re.sub(r"^\s*[\*\-•]\s+", "", t, flags=re.M)
    t = re.sub(r"\*(?=\S)(.*?)(?<=\S)\*", r"\1", t)
    t = re.sub(r"https?://\S+", "", t)
    t = re.sub(r"[ \t]+", " ", t)
    t = re.sub(r"\n{3,}", "\n\n", t)
    return t.strip()


def speech_text(text, limit=650):
    """Bolne ke liye: ek line me, lamba ho to vaakya par kaat do."""
    t = re.sub(r"\s*\n+\s*", ". ", clean_reply(text))
    t = re.sub(r"\.\s*\.", ".", t)
    if len(t) <= limit:
        return t
    cut = t[:limit]
    end = max(cut.rfind(". "), cut.rfind("? "), cut.rfind("! "))
    if end < limit * 0.4:
        end = cut.rfind(" ")
    return cut[:end + 1].strip() + " Baaki jawab screen par hai."


# ---------------------------------------------------------------- CLIENT ----
class GeminiClient:
    def __init__(self, get_key, get_verbosity=lambda: "Balanced", base_url=None,
                 get_model=None, set_model=None):
        self.get_key = get_key
        self.get_verbosity = get_verbosity
        self.base_url = (base_url or BASE_URL).rstrip("/")
        self.model = get_model() if get_model else None
        self._set_model = set_model
        self.last_detail = ""
        self.history = []                  # [{"role": "user"/"model", "text": ...}]

    # ---- memory ----
    def clear(self):
        self.history = []

    def _trim(self):
        self.history = self.history[-MAX_TURNS * 2:]
        while len(self.history) > 2 and sum(len(h["text"]) for h in self.history) > MAX_HISTORY_CHARS:
            self.history = self.history[2:]

    # ---- low level ----
    def _headers(self):
        key = (self.get_key() or "").strip()
        if not key:
            raise AIError("nokey")
        return {"Content-Type": "application/json; charset=utf-8", "x-goog-api-key": key}

    def _map_error(self, status, body):
        message = ""
        try:
            message = json.loads(body).get("error", {}).get("message", "")
        except Exception:
            message = (body or "")[:200]
        low = message.lower()
        if status == 429 or "quota" in low or "resource_exhausted" in low:
            return AIError("quota", message)
        if status in (400, 401, 403) and ("api key" in low or "api_key" in low):
            return AIError("badkey", message)
        if status in (401,):
            return AIError("badkey", message)
        if status == 403:
            return AIError("forbidden", message)
        if status == 404 or (status == 400 and ("model" in low and ("not found" in low or "not supported" in low))):
            return AIError("nomodel", message)
        if status >= 500:
            return AIError("server", message)
        return AIError("other", message)

    def discover(self):
        status, body = http_request("GET", self.base_url + "/models?pageSize=200", self._headers())
        if status != 200:
            raise self._map_error(status, body)
        models = json.loads(body).get("models", [])
        names = [m.get("name", "") for m in models
                 if "generateContent" in (m.get("supportedGenerationMethods") or [])]
        return rank_models(names)

    def _models_to_try(self, force=False):
        if self.model and not force:
            return [self.model]
        order = self.discover()
        return (order[:3] or list(PREFERRED[:2]))

    def _payload(self, user_text):
        contents = [{"role": h["role"], "parts": [{"text": h["text"]}]} for h in self.history]
        contents.append({"role": "user", "parts": [{"text": user_text}]})
        return {
            "systemInstruction": {"parts": [{"text": system_prompt(self.get_verbosity())}]},
            "contents": contents,
            "generationConfig": {"temperature": 0.7, "maxOutputTokens": 2048},
        }

    @staticmethod
    def _parse(body):
        data = json.loads(body)
        if (data.get("promptFeedback") or {}).get("blockReason"):
            raise AIError("blocked", str(data.get("promptFeedback")))
        cands = data.get("candidates") or []
        if not cands:
            raise AIError("empty", body[:200])
        parts = ((cands[0].get("content") or {}).get("parts")) or []
        text = "".join(p.get("text", "") for p in parts if not p.get("thought")).strip()
        if not text:
            if cands[0].get("finishReason") in ("SAFETY", "BLOCKLIST", "PROHIBITED_CONTENT"):
                raise AIError("blocked", str(cands[0].get("finishReason")))
            raise AIError("empty", body[:200])
        return text

    # ---- public ----
    def ask(self, user_text):
        """Return (True, jawab) ya (False, error message). Blocking hai: thread me chalaiye."""
        user_text = " ".join(str(user_text).split())
        try:
            headers = self._headers()
            tries = self._models_to_try()
            payload = json.dumps(self._payload(user_text)).encode("utf-8")
            last = AIError("other")
            for attempt in range(2):
                for model in tries:
                    url = "%s/models/%s:generateContent" % (self.base_url, model)
                    status, body = http_request("POST", url, headers, payload)
                    if status == 200:
                        reply = clean_reply(self._parse(body))
                        if not reply:
                            raise AIError("empty")
                        if model != self.model:
                            self.model = model
                            if self._set_model:
                                self._set_model(model)
                        self.history += [{"role": "user", "text": user_text},
                                         {"role": "model", "text": reply}]
                        self._trim()
                        return True, reply
                    last = self._map_error(status, body)
                    if last.kind not in ("nomodel", "quota"):
                        raise last          # galat key, server error... agla model bekaar hai
                if attempt == 0 and self.model:
                    self.model = None          # purana naam band ho gaya ho to dobara dhundo
                    tries = self._models_to_try(force=True)
                    continue
                break
            raise last
        except AIError as err:
            print("JARVIS AI error:", err.kind, err.detail[:200])
            self.last_detail = err.detail
            return False, err.message
        except Exception as exc:                 # JSON/parse waghera
            print("JARVIS AI unexpected:", repr(exc)[:200])
            return False, MESSAGES["other"]


# ------------------------------------------------------- MATH vs AI GATE ----
_MATH_WORDS = set("""plus minus times into multiply multiplied divide divided by jodo ghatao
guna gunaa gunnah bhaag bhag power raised to the of square root cube sin cos tan sine cosine
tangent log ln factorial percent percentage ka ke ki degree degrees point mod modulo sqrt
calculate calculation compute what is whats kitna kitni hota hote hai hain hisab karo kar do
solve answer jawab batao bataiye please jarvis total equal equals vargmool varg ghan and
zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen
sixteen seventeen eighteen nineteen twenty thirty forty fifty sixty seventy eighty ninety
hundred thousand lakh lac crore million billion shunya sunya ek do teen char chaar panch paanch
chhe cheh saat aath nau das gyarah barah terah chaudah pandrah solah satrah atharah unnis bees
ikkees baees teis chaubis pachis pachchis chhabbis sattais athais untees tees chalees chaalis
pachaas saath sattar assi nabbe sau hazaar hazar karod natural""".split())


def is_simple_math(text):
    """True agar sawal sirf number/hisaab ka hai (jaise '25 plus 5', 'sin 30'),
    False agar kisi cheez ke baare me sawal hai (jaise 'what is inflation')."""
    tokens = re.findall(r"[a-z']+|\d+(?:\.\d+)?|[+\-*/%^]", str(text).lower())
    if not tokens:
        return False
    other = [t for t in tokens if not re.match(r"^(\d|[+\-*/%^])", t)
             and t.replace("'", "") not in _MATH_WORDS]
    has_number = any(re.match(r"^\d", t) for t in tokens) or any(
        t in _MATH_WORDS and t not in ("what", "is", "whats", "the", "of", "to", "by", "and",
                                       "ka", "ke", "ki", "hai", "hain", "karo", "please",
                                       "jarvis", "batao", "bataiye", "kar", "do", "kitna",
                                       "kitni", "hota", "hote", "answer", "jawab", "total",
                                       "calculate", "compute", "solve", "hisab", "calculation")
        for t in tokens)
    return not other and has_number
