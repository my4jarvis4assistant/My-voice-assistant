"""JARVIS: WhatsApp par naam bolkar message / voice call / video call (app ke andar).

Kya hota hai:
  "saket ko whatsapp par message bhejo ki main late aaunga"  -> naam dhoondhta hai, bolta hai kya bhejna hai,
                                                                 "bhej dun?" poochta hai, haan par WhatsApp me bhejta hai
  "saket ko whatsapp par video call karo" / "priya ko whatsapp call lagao" -> seedha WhatsApp call
  aadha naam ("saket") bolo to bhi chalega; kai milen to list dikhakar "2 ko karo" se chunte hain.
Instagram / Facebook / Messenger par message ya call Android me bahar se mumkin nahi (unke paas
koi aisa darwaza nahi), isliye wahan Jarvis saaf bata deta hai.
Message ko apne aap 'Send' karwane ke liye Accessibility service On honi chahiye (Settings me row hai);
warna chat khulti hai aur text likha hua milta hai, bas Send dabana hota hai.
"""
import re
import time

import jarvis_calls as jc

APPS = {
    "whatsapp": ("whatsapp", "watsapp", "whatsap", "vatsapp", "whats", "wa", "whatsup", "whatsapps", "whatapp"),
    "instagram": ("instagram", "insta", "instagrm", "instagraam"),
    "facebook": ("facebook", "fb", "fecbook", "facebok"),
    "messenger": ("messenger", "masenger"),
    "telegram": ("telegram", "telegrm"),
}
APP_NAMES = {"whatsapp": "WhatsApp", "instagram": "Instagram", "facebook": "Facebook",
             "messenger": "Messenger", "telegram": "Telegram"}
APP_WORDS = {w for ws in APPS.values() for w in ws}
VIDEO_WORDS = {"video", "vdo", "vedio", "videocall", "vidio"}
VOICE_WORDS = {"voice", "audio", "normal"}
MSG_WORDS = {"message", "msg", "messege", "massage", "messeg", "text", "sms", "bhejo", "bhej", "bhejna",
             "send", "likho", "likh", "bhejdo", "bhejiye", "bhejein", "bhejde"}
NOISE = {"ek", "ko", "ka", "ki", "ke", "se", "par", "pe", "me", "mein", "to", "karo", "kro", "kar", "kare",
         "karna", "kariye", "kijiye", "kardo", "krdo", "do", "de", "dena", "dijiye", "mujhe", "mera", "meri",
         "jarvis", "hey", "hello", "hi", "please", "plz", "a", "the", "on", "via", "through", "for", "abhi",
         "zara", "jara", "wala", "wali", "contact", "naam", "number", "phone", "call", "calls", "lagao",
         "laga", "lagana", "dial", "kall", "caal", "cal", "milao", "can", "you", "will", "make", "now",
         "voice", "audio", "normal", "kro", "krna", "kre", "kardena", "bol", "bolo", "keh", "kaho", "bhi"}
SKIP_WORDS = APP_WORDS | VIDEO_WORDS | MSG_WORDS | NOISE

_MARKER = re.compile(
    r"\b(?:ki|kee|ye|yeh|that|saying|likho|likh\s+do|likh\s+kar|bolo|bol\s+do|keh\s+do|kehdo|kaho|"
    r"message\s+hai)\b[\s,:]*(.+)$", re.I)
_VERB = re.compile(r"\b(?:bhejo|bhej\s*do|bhejdo|bhejna|bhejiye|bhejein|bhejde|send(?:\s+karo|\s+kro)?)\b[\s,:]*(.+)$",
                   re.I)
_LEAD = re.compile(r"^(?:(?:ki|kee|ye|yeh|that|saying|ke|ko|to|message|msg|text|karo|kro|do|de|bolo|likho|bhejo|"
                   r"whatsapp|par|pe|me|mein|ek)\b[\s,:]*)+", re.I)


def detect_app(w):
    for t in w:
        for key, names in APPS.items():
            if t in names:
                return key
    return ""


def parse_social(utterance):
    """None = ye WhatsApp/social wali baat nahi. Warna dict:
    kind ('message'/'call'), app, video, name (shayad ''), body (None = abhi pata nahi), ambiguous."""
    u = " ".join(str(utterance or "").split())
    w = jc.words(u)
    if not w:
        return None
    for t in w:
        if t in jc.NOT_A_CALL and t not in MSG_WORDS and t not in APP_WORDS:
            return None
    app = detect_app(w)
    video = any(t in VIDEO_WORDS for t in w)
    has_msg = any(t in MSG_WORDS for t in w)
    has_call = any(t in jc.CALL_WORDS for t in w) or any(t == "videocall" for t in w)
    if has_msg and not (has_call and not any(t in ("message", "msg", "messege", "massage", "text", "sms")
                                             for t in w)):
        kind = "message"
    elif has_call or video:
        kind = "call"
    elif app and _MARKER.search(u):
        kind = "message"                    # "saket ko whatsapp par bolo ki ..."
    else:
        return None
    if kind == "call" and not app and not video:
        return None                         # seedha phone call: jarvis_calls sambhalega
    if kind == "message" and len(w) > 40:
        return None
    body = None
    head = u
    ambiguous = False
    if kind == "message":
        m = _MARKER.search(u)
        if m and m.start() > 0:
            head = u[:m.start()]
            body = m.group(1)
        else:
            m = _VERB.search(u)
            if m and m.start() > 0 and jc.words(u[:m.start()]) and \
                    any(t not in SKIP_WORDS for t in jc.words(u[:m.start()])):
                head = u[:m.start()]            # naam pehle aaya: "saket ko message bhejo hello"
                body = m.group(1)
            elif m:
                ambiguous = True                # "send message to saket hello how are you"
        if body is not None:
            body = _LEAD.sub("", body).strip()
            if not body:
                body = None
    name_tokens = [t for t in jc.words(head) if t not in SKIP_WORDS]
    if kind == "message" and ambiguous:
        tail = jc.words(u)
        try:
            i = max(idx for idx, t in enumerate(tail) if t in ("to", "ko"))
            tail_tokens = tail[i + 1:]
        except ValueError:
            tail_tokens = tail
        name_tokens = list(tail_tokens)       # contact milne par naam/message alag honge
    return {"kind": kind, "app": app or "whatsapp", "app_said": bool(app), "video": video,
            "name": " ".join(name_tokens), "body": body, "ambiguous": ambiguous}


def split_name_body(tokens, contacts):
    """'saket hello how are you' -> contact milne tak pehle 1-3 shabd naam, baaki message."""
    for k in (3, 2, 1):
        if len(tokens) < k:
            continue
        cand = " ".join(tokens[:k])
        if jc.find(cand, contacts, 4):
            rest = " ".join(tokens[k:])
            return cand, (rest or None)
    return " ".join(tokens), None


YES = {"haan", "han", "ha", "haa", "yes", "yeah", "yep", "bhej", "bhejo", "send", "ok", "okay", "kar", "karo",
       "theek", "thik", "sahi", "correct", "sure", "bilkul", "hanji", "haanji", "ji"}
NO = {"nahi", "nhi", "no", "cancel", "mat", "ruko", "stop", "galat", "nope", "rehne", "rahne", "chhodo", "chodo"}


def yes_no(text):
    w = jc.words(text)
    if any(t in NO for t in w):
        return "no"
    if any(t in YES for t in w):
        return "yes"
    return ""


# ---------------------------------------------------------------- Android --
MIME_BASE = "vnd.android.cursor.item/vnd.com.whatsapp"


def normalize_number(num):
    d = re.sub(r"\D", "", num or "")
    if len(d) == 10:
        return "91" + d
    if len(d) == 11 and d.startswith("0"):
        return "91" + d[1:]
    return d


def load_whatsapp_contacts(app):
    """WhatsApp wale contacts: [{'name','cid','ids':{'profile','voip.call','video.call'},'pkg','number'}]"""
    from jnius import autoclass
    Data = autoclass("android.provider.ContactsContract$Data")
    resolver = app.activity.getContentResolver()
    cur = resolver.query(Data.CONTENT_URI, ["_id", "contact_id", "display_name", "mimetype"],
                         "mimetype LIKE ?", [MIME_BASE + "%"], None)
    if cur is None:
        raise PermissionError("contacts")
    people = {}
    try:
        while cur.moveToNext():
            did, cid, name, mime = int(cur.getLong(0)), int(cur.getLong(1)), cur.getString(2), cur.getString(3)
            if not name or not mime:
                continue
            mime = str(mime)
            business = ".w4b." in mime
            kind = mime.rsplit("whatsapp.", 1)[-1].replace("w4b.", "")
            p = people.setdefault((cid, business), {"name": str(name), "cid": cid, "ids": {},
                                                    "pkg": "com.whatsapp.w4b" if business else "com.whatsapp",
                                                    "mime": {}, "number": ""})
            p["ids"][kind] = did
            p["mime"][kind] = mime
    finally:
        cur.close()
    out = [p for p in people.values() if p["ids"]]
    names_seen = {}
    for p in out:                               # normal WhatsApp ko Business par tarjeeh
        names_seen.setdefault(p["cid"], p)
        if p["pkg"] == "com.whatsapp":
            names_seen[p["cid"]] = p
    return list(names_seen.values())


def phone_for_contact(app, cid):
    from jnius import autoclass
    Phone = autoclass("android.provider.ContactsContract$CommonDataKinds$Phone")
    cur = app.activity.getContentResolver().query(Phone.CONTENT_URI, ["data1"], "contact_id=?",
                                                  [str(cid)], None)
    if cur is None:
        return ""
    try:
        while cur.moveToNext():
            n = normalize_number(cur.getString(0))
            if n:
                return n
    finally:
        cur.close()
    return ""


def launch_whatsapp_call(app, person, video):
    from jnius import autoclass
    Intent = autoclass("android.content.Intent")
    Uri = autoclass("android.net.Uri")
    key = "video.call" if video else "voip.call"
    did = person["ids"].get(key)
    if not did:
        raise RuntimeError("is contact ke liye WhatsApp " + ("video" if video else "voice") + " call nahi mila")
    intent = Intent(Intent.ACTION_VIEW)
    intent.setDataAndType(Uri.parse("content://com.android.contacts/data/" + str(did)),
                          person["mime"][key])
    intent.setPackage(person["pkg"])
    intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
    app.activity.startActivity(intent)


def arm_autosend(app):
    """Accessibility service ko 25 second ke liye bolo ki WhatsApp me 'Send' dabana hai."""
    try:
        ed = app.activity.getSharedPreferences("jarvis_prefs", 0).edit()
        ed.putLong("access_send_until", int(time.time() * 1000) + 25000)
        ed.apply()
    except Exception as exc:
        print("arm_autosend error:", exc)


def launch_whatsapp_chat(app, person, number, text):
    from jnius import autoclass
    Intent = autoclass("android.content.Intent")
    Uri = autoclass("android.net.Uri")
    URLEncoder = autoclass("java.net.URLEncoder")
    enc = str(URLEncoder.encode(text, "UTF-8"))
    intent = Intent(Intent.ACTION_VIEW, Uri.parse("https://wa.me/" + number + "?text=" + enc))
    intent.setPackage(person["pkg"])
    intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
    arm_autosend(app)
    app.activity.startActivity(intent)


def accessibility_enabled(app):
    try:
        from jnius import autoclass
        Secure = autoclass("android.provider.Settings$Secure")
        val = Secure.getString(app.activity.getContentResolver(), "enabled_accessibility_services")
        return bool(val and "JarvisAccessService" in str(val))
    except Exception:
        return False


# ------------------------------------------------------------------ flow ---
def install_social(app, loader=None, phone=None, call_launcher=None, chat_launcher=None,
                   permission=None, autosend=None):
    """app._jarvis_try_social(command) lagata hai. True = yahin sambhal liya."""
    from kivy.clock import Clock
    st = {"choices": None, "job": None, "await_body": False, "confirm": False, "await_name": False}
    load = loader or (lambda: load_whatsapp_contacts(app))
    get_phone = phone or (lambda cid: phone_for_contact(app, cid))
    do_call = call_launcher or (lambda person, video: launch_whatsapp_call(app, person, video))
    do_chat = chat_launcher or (lambda person, number, text: launch_whatsapp_chat(app, person, number, text))
    perm = permission or (lambda p: jc.has_permission(app, p))
    auto_ok = autosend or (lambda: accessibility_enabled(app))

    def say(text, spoken=None, relisten=False):
        def run(dt):
            try:
                app.set_status(text)
                app.speak(spoken or text)
                if relisten:
                    Clock.schedule_once(lambda d: app.listen(), 0.8)
            except Exception as exc:
                print("social say error:", exc)
        Clock.schedule_once(run, 0)

    def reset():
        st.update(choices=None, job=None, await_body=False, confirm=False, await_name=False)

    def act(person):
        job = st["job"]
        shown = jc.speakable(person["name"])
        if job["kind"] == "call":
            try:
                do_call(person, job["video"])
                say(shown + " ko WhatsApp par " + ("video" if job["video"] else "voice") + " call laga raha hoon.")
            except Exception as exc:
                print("wa call error:", repr(exc))
                say(str(exc)[:80] if "WhatsApp" in str(exc) else "WhatsApp call nahi lag paya.")
            reset()
            return
        job["person"] = person
        if not job.get("body"):
            st["await_body"] = True
            say(shown + " ko kya message bhejna hai?", relisten=True)
            return
        ask_confirm()

    def ask_confirm():
        job = st["job"]
        shown = jc.speakable(job["person"]["name"])
        st["confirm"] = True
        say(shown + " ko WhatsApp par bhejna hai: " + job["body"] + "\nBhej dun?",
            shown + " ko WhatsApp par bhejna hai. " + job["body"] + ". Bhej dun?", relisten=True)

    def send_now():
        job = st["job"]
        person = job["person"]
        shown = jc.speakable(person["name"])
        try:
            number = person.get("number") or get_phone(person["cid"])
            if not number:
                say(shown + " ka number nahi mila.")
                reset()
                return
            do_chat(person, number, job["body"])
            if auto_ok():
                say(shown + " ko message bhej raha hoon.")
            else:
                say("Chat khol di hai. Bas Send dabaiye. (Apne aap bhejne ke liye Settings me Accessibility On kijiye)")
        except Exception as exc:
            print("wa chat error:", repr(exc))
            say("WhatsApp khul nahi paya.")
        reset()

    def resolve(job):
        if not perm("android.permission.READ_CONTACTS"):
            jc.ask_permission(app)
            say("Contacts ki permission chahiye. Allow dabaiye, phir dobara boliye.")
            reset()
            return
        try:
            people = load()
        except Exception as exc:
            print("wa contacts error:", repr(exc))
            say("WhatsApp contacts padh nahi paya. Calling permission allow kijiye.")
            reset()
            return
        pairs = [(p["name"], str(p["cid"])) for p in people]
        by_cid = {str(p["cid"]): p for p in people}
        name = job["name"]
        if job["kind"] == "message" and job.get("ambiguous") and not job.get("body"):
            name, body = split_name_body(jc.words(name), pairs)
            job["name"], job["body"] = name, body
        if not name.strip():
            st["await_name"] = True
            say("Kisko?", relisten=True)
            return
        found = jc.find(name, pairs, 4)
        if not found:
            say(name + " naam ka WhatsApp contact nahi mila.")
            reset()
        elif len(found) == 1:
            act(by_cid[found[0][1]])
        else:
            st["choices"] = [(n, "", s, by_cid[c]) for (n, c, s) in found]
            triples = [(n, "", s) for (n, _c, s) in found]
            say(jc.choices_text(triples).replace("Ye contacts mile.", "Ye WhatsApp contacts mile."),
                jc.choices_speech(triples), relisten=True)

    def try_social(command):
        text = str(command)
        if st["confirm"]:
            ans = yes_no(text)
            if ans == "yes":
                st["confirm"] = False
                send_now()
                return True
            if ans == "no":
                reset()
                say("Theek hai, message nahi bheja.")
                return True
            if parse_social(text) is None:
                say("Bhej dun? Haan ya nahi boliye.", relisten=True)
                return True
            reset()
        if st["await_body"]:
            st["await_body"] = False
            if parse_social(text) is None or yes_no(text) == "":
                st["job"]["body"] = text.strip()
                ask_confirm()
                return True
            reset()
        if st["await_name"]:
            st["await_name"] = False
            st["job"]["name"] = " ".join(t for t in jc.words(text) if t not in SKIP_WORDS)
            resolve(st["job"])
            return True
        if st["choices"] is not None:
            items = st["choices"]
            pick = jc.parse_choice(text, len(items))
            if pick > 0:
                st["choices"] = None
                act(items[pick - 1][3])
                return True
            if pick < 0:
                reset()
                say("Theek hai, rehne diya.")
                return True
            if parse_social(text) is None:
                say("Samajh nahi aaya. Number boliye, jaise do.", relisten=True)
                return True
            st["choices"] = None
        job = parse_social(text)
        if job is None:
            return False
        if job["app"] != "whatsapp":
            nm = APP_NAMES.get(job["app"], job["app"])
            say(nm + " par message ya call Android me bahar se mumkin nahi hai. WhatsApp par kar sakta hoon, "
                "WhatsApp bolkar dekhiye.")
            return True
        st["job"] = job
        resolve(job)
        return True

    app._jarvis_try_social = try_social
    app._jarvis_social_state = st
    return try_social
