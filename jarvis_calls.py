"""JARVIS: naam se call (app ke andar). main.py ko nahi badalta.

- "saket ko call karo", "jarvis saket jha ko phone lagao" jaise kisi bhi tareeke se bola gaya naam samajhta hai
- saved naam "saket jha(gau)" ho to bhi, aur Hinglish spelling ka fark (saket/sakit) maaf karta hai
- ek hi sahi contact ho to seedha call lagata hai
- 2-3 contacts milen to sab ke naam + number dikhata/bolta hai, phir "2 ko call karo" bolne par wahi call lagata hai
Ye logic src/JarvisContactMatch.java (home screen panel) ka Python version hai.
"""
import re

CALL_WORDS = {
    "call", "calls", "kall", "caal", "kaal", "cal", "dial", "phone", "fone", "milao", "milana",
    "lagao", "laga", "lagana", "lagado", "lagade", "lagadena"}

FILLER = {
    "jarvis", "hey", "hello", "hi", "ok", "okay", "please", "plz", "ko", "ka", "ki", "ke", "se",
    "kro", "karo", "kar", "karna", "kariye", "kijiye", "karein", "krna", "kre", "kare", "kardo", "kardena",
    "do", "de", "dena", "dijiye", "diye", "dial", "phone", "fone", "mobile", "number", "mujhe",
    "mera", "meri", "mere", "hume", "humko", "contact", "naam", "wale", "wali", "wala", "ek", "zara",
    "jara", "abhi", "now", "to", "tu", "pe", "par", "on", "me", "mein", "karke", "phir", "can", "you",
    "could", "will", "make", "a", "the", "call", "calls", "kall", "caal", "kaal", "cal", "milao",
    "milana", "lagao", "laga", "lagana", "lagado", "lagade", "lagadena", "baat", "karni", "karwa",
    "karwao", "krdo", "krde", "kr", "bol", "bolo", "bulao", "bula"}

NOT_A_CALL = {
    "open", "kholo", "khol", "launch", "alarm", "timer", "remind", "reminder", "note", "settings",
    "setting", "search", "youtube", "play", "message", "sms", "whatsapp", "send", "install", "volume",
    "wifi", "bluetooth", "torch", "flashlight", "brightness", "history", "log", "logs", "recent"}


def words(s):
    return re.findall(r"[^\W_]+", (s or "").lower())


def parse_call_request(utterance):
    """Naam (str) lautata hai; "" = call ka irada hai par naam nahi bola; None = call ki baat nahi."""
    w = words(utterance)
    has_call = False
    for t in w:
        if t in NOT_A_CALL:
            return None
        if t in CALL_WORDS:
            has_call = True
    if not has_call:
        return None
    name = [t for t in w if t not in FILLER]
    if len(name) > 4:
        return None
    return " ".join(name)


def phon(s):
    """saket/sakit/sakeet -> ek hi chabi."""
    x = s.lower()
    for a, b in (("ph", "f"), ("ck", "k"), ("kh", "k"), ("gh", "g"), ("bh", "b"), ("dh", "d"),
                 ("th", "t"), ("sh", "s"), ("ch", "c"), ("w", "v"), ("z", "j"), ("q", "k"),
                 ("x", "ks"), ("y", "i")):
        x = x.replace(a, b)
    out = []
    prev = ""
    for ch in x:
        if not ch.isalnum() or ch == "h":
            continue
        if ch in "aeiou":
            ch = "a"
        if ch == prev:
            continue
        out.append(ch)
        prev = ch
    return "".join(out)


def lev(a, b):
    prev = list(range(len(b) + 1))
    for i in range(1, len(a) + 1):
        cur = [i] + [0] * len(b)
        for j in range(1, len(b) + 1):
            c = 0 if a[i - 1] == b[j - 1] else 1
            cur[j] = min(cur[j - 1] + 1, prev[j] + 1, prev[j - 1] + c)
        prev = cur
    return prev[len(b)]


def token_score(q, c):
    if q == c:
        return 1.0
    if len(q) >= 3 and c.startswith(q):
        return 0.92
    pq, pc = phon(q), phon(c)
    if not pq or not pc:
        return 0.0
    if pq == pc:
        return 0.9
    if len(pq) >= 3 and pc.startswith(pq):
        return 0.82
    if len(pq) >= 4 and lev(pq, pc) <= 1:
        return 0.78
    ratio = 1.0 - float(lev(q, c)) / max(len(q), len(c))
    if len(q) >= 4 and ratio >= 0.75:
        return ratio * 0.85
    return 0.0


def _split_name(contact_name):
    """(bracket ke bahar ke shabd, sab shabd)"""
    main, all_w = [], []
    in_paren = False
    buf = ""
    cn = (contact_name or "").lower()
    for ch in cn + " ":
        if ch.isalnum():
            buf += ch
            continue
        if buf:
            all_w.append(buf)
            if not in_paren:
                main.append(buf)
            buf = ""
        if ch in "([{":
            in_paren = True
        elif ch in ")]}":
            in_paren = False
    return main, all_w


def score(spoken, contact_name):
    q = words(spoken)
    if not q:
        return 0.0
    main, all_w = _split_name(contact_name)
    if not all_w:
        return 0.0
    if "".join(q) == "".join(main):
        return 1.0
    total = 0.0
    all_matched = True
    for t in q:
        best = max(token_score(t, c) for c in all_w)
        if best <= 0:
            all_matched = False
        total += best
    avg = total / len(q)
    if not all_matched:
        avg *= 0.5
    extra = max(0, len(main) - len(q))
    return max(0.0, avg - 0.02 * extra)


def digits(number):
    d = re.sub(r"[^0-9]", "", number or "")
    return d[-10:] if len(d) > 10 else d


def find(spoken, contacts, max_n=4):
    """contacts = [(name, number)]. Sabse achhe match, ek number ek hi baar."""
    scored = []
    best = 0.0
    for name, number in contacts:
        if not name or not number:
            continue
        s = score(spoken, name)
        if s >= 0.7:
            scored.append((s, name, number))
            best = max(best, s)
    scored.sort(key=lambda x: -x[0])
    out, seen = [], set()
    for s, name, number in scored:
        if s < best - 0.08:
            continue
        key = digits(number)
        if not key or key in seen:
            continue
        seen.add(key)
        out.append((name, number, s))
        if len(out) >= max_n:
            break
    return out


_NUMS = {
    1: ("1", "one", "ek", "won", "pehla", "pehle", "pahla", "pahle", "first", "1st", "pehli", "pahli"),
    2: ("2", "two", "do", "dow", "to", "too", "tu", "dusra", "dusre", "doosra", "doosre", "second",
        "2nd", "dusri", "doosri"),
    3: ("3", "three", "teen", "tin", "tree", "teesra", "teesre", "tisra", "third", "3rd", "teesri"),
    4: ("4", "four", "for", "char", "chaar", "chautha", "chauthe", "fourth", "4th"),
    5: ("5", "five", "panch", "paanch", "paanchva", "panchva", "fifth", "5th"),
}
_CANCEL = {"cancel", "nahi", "nhi", "mat", "rehne", "rahne", "chhodo", "chodo", "stop", "no", "band"}


def parse_choice(utterance, n):
    """1..n = chunav, -1 = rehne do, 0 = samajh nahi aaya."""
    w = words(utterance)
    if any(t in _CANCEL for t in w):
        return -1
    for i, t in enumerate(w):
        prev = w[i - 1] if i else ""
        v = 0
        for num, names in _NUMS.items():
            if t in names:
                v = num
                break
        if v == 2 and t in ("do", "dow") and prev in ("kar", "karo", "laga", "lagao", "kr", "kro"):
            continue
        if 0 < v <= n:
            return v
        if t in ("last", "aakhri", "akhri", "antim"):
            return n
    return 0


def speakable(name):
    return re.sub(r"\s+", " ", re.sub(r"[()\[\]{}]", " ", name or "")).strip()


def choices_text(items):
    lines = ["Ye contacts mile. Bolkar chuniye (jaise \"2 ko call karo\"):", ""]
    for i, (name, number, _s) in enumerate(items, 1):
        lines.append("%d.  %s" % (i, name))
        lines.append("      %s" % number)
    return "\n".join(lines)


def choices_speech(items):
    parts = ["Mujhe %d contacts mile." % len(items)]
    for i, (name, number, _s) in enumerate(items, 1):
        nm = speakable(name)
        same = any(j != i - 1 and speakable(o[0]).lower() == nm.lower() for j, o in enumerate(items))
        d = digits(number)
        piece = "Number %d, %s" % (i, nm)
        if same and len(d) >= 4:
            piece += ", number " + " ".join(d[-4:]) + " par khatam"
        parts.append(piece + ".")
    parts.append("Kaun sa call karun?")
    return " ".join(parts)


# ------------------------------------------------------------ Android ------
def load_contacts(app):
    """Phone ke sab contacts [(naam, number)]. Permission na ho to PermissionError."""
    from jnius import autoclass
    Phone = autoclass("android.provider.ContactsContract$CommonDataKinds$Phone")
    activity = app.activity
    cursor = activity.getContentResolver().query(
        Phone.CONTENT_URI, [Phone.DISPLAY_NAME, Phone.NUMBER], None, None, None)
    out = []
    if cursor is None:
        raise PermissionError("contacts")
    try:
        while cursor.moveToNext():
            name = cursor.getString(0)
            number = cursor.getString(1)
            if name and number:
                out.append((str(name), str(number)))
    finally:
        cursor.close()
    return out


def has_permission(app, perm):
    try:
        from jnius import autoclass
        PM = autoclass("android.content.pm.PackageManager")
        return app.activity.checkSelfPermission(perm) == PM.PERMISSION_GRANTED
    except Exception:
        return True


def place_call(app, number):
    """CALL_PHONE mili ho to seedha call, warna dialer me number."""
    from jnius import autoclass
    Intent = autoclass("android.content.Intent")
    Uri = autoclass("android.net.Uri")
    direct = has_permission(app, "android.permission.CALL_PHONE")
    clean = re.sub(r"[^0-9+]", "", number)
    intent = Intent(Intent.ACTION_CALL if direct else Intent.ACTION_DIAL, Uri.parse("tel:" + clean))
    intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
    app.activity.startActivity(intent)
    return direct


def ask_permission(app):
    try:
        from android.permissions import request_permissions
        request_permissions(["android.permission.READ_CONTACTS", "android.permission.CALL_PHONE"])
    except Exception as exc:
        print("permission request error:", exc)


# ------------------------------------------------------------ app hook -----
def install_calls(app, loader=None, caller=None, permission=None):
    """app.process_command ke aage "X ko call karo" ka logic lagata hai.
    Ye jarvis_ui ke process_command wrapper ke andar app._jarvis_try_call(cmd) se bulaya jata hai."""
    from kivy.clock import Clock
    state = {"choices": None, "await_name": False}
    load = loader or (lambda: load_contacts(app))
    call = caller or (lambda number: place_call(app, number))
    perm_check = permission or (lambda p: has_permission(app, p))

    def say(text, spoken=None, relisten=False):
        def run(dt):
            try:
                app.set_status(text)
                app.speak(spoken or text)
                if relisten:
                    Clock.schedule_once(lambda d: app.listen(), 0.8)
            except Exception as exc:
                print("call say error:", exc)
        Clock.schedule_once(run, 0)

    def dial(name, number):
        try:
            direct = call(number)
            nm = speakable(name)
            say(nm + (" ko call kar raha hoon." if direct else " ka number dialer me khol diya."))
        except Exception as exc:
            print("call error:", repr(exc))
            say("Call nahi lag paya.")

    def by_name(wanted):
        if not wanted.strip():
            state["await_name"] = True
            say("Kisko call karun?", relisten=True)
            return
        if not perm_check("android.permission.READ_CONTACTS"):
            ask_permission(app)
            say("Contacts ki permission chahiye. Allow dabaiye, phir dobara boliye.")
            return
        try:
            found = find(wanted, load(), 4)
        except Exception as exc:
            print("contacts error:", repr(exc))
            say("Contacts padh nahi paya. Settings me Calling permission allow kijiye.")
            return
        if not found:
            say(wanted + " naam ka contact nahi mila.")
        elif len(found) == 1:
            dial(found[0][0], found[0][1])
        else:
            state["choices"] = found
            say(choices_text(found), choices_speech(found), relisten=True)

    def try_call(command):
        """True = call ka kaam yahin sambhal liya, main.py ko mat do."""
        text = str(command)
        if state["choices"] is not None:
            items = state["choices"]
            pick = parse_choice(text, len(items))
            if pick > 0:
                state["choices"] = None
                dial(items[pick - 1][0], items[pick - 1][1])
                return True
            if pick < 0:
                state["choices"] = None
                say("Theek hai, call nahi kar raha.")
                return True
            again = parse_call_request(text)
            if not again:
                say(choices_text(items), "Samajh nahi aaya. Number boliye, jaise do.", relisten=True)
                return True
            state["choices"] = None
        if state["await_name"]:
            state["await_name"] = False
            nm = parse_call_request("call " + text)
            by_name(nm if nm else text)
            return True
        name = parse_call_request(text)
        if name is None:
            return False
        if name and not re.search(r"[a-z]", name) and len(re.sub(r"\D", "", name)) >= 5:
            return False                      # "call 98765 43210": number hai, main.py dialer kholega
        by_name(name)
        return True

    app._jarvis_try_call = try_call
    app._jarvis_call_state = state
    return try_call
