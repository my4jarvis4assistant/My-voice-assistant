"""JARVIS: aaye hue messages / missed calls ke sawaal (app ke andar bole gaye).

"kitne message aaye", "kiske message aaye hain", "koi call aaya?", "WhatsApp par kya aaya",
"messages padh kar sunao", "jawab de do" - sab kuch Java service (JarvisOverlayService) sambhalti hai,
kyunki notifications wahi padhti hai. Yahan sirf pehchana jata hai ki baat inbox ki hai ya nahi, aur
use service ko bhej diya jata hai (jawab wahi bolti hai).
Ye pehchan JarvisInbox.parse (Java) jaisi hi hai.
"""
import jarvis_calls as jc


def _s(*a):
    return set(a)


QUERY = _s("aaye", "aaya", "aayi", "aayee", "aya", "aye", "aai", "aayein", "mile", "mila", "mili", "kitne",
           "kitni", "kitna", "kiske", "kiska", "kiski", "kisne", "naye", "naya", "nayi", "unread", "pending",
           "new", "received", "came", "missed", "miss", "padho", "padh", "sunao", "suna", "dikhao", "batao",
           "bataiye", "bata", "read", "check", "kisi", "koi", "kuch")
MSG = _s("message", "messages", "msg", "msgs", "sandesh", "massage", "messeg", "messege", "text", "texts", "sms",
         "notification", "notifications", "dm", "dms", "whatsapp", "watsapp", "whatsap", "vatsapp", "insta",
         "instagram", "messenger", "telegram", "chat", "chats")
CALL = _s("call", "calls", "caal", "kall", "missed", "miss")
SEND = _s("bhejo", "bhej", "bhejna", "send", "likho", "likh", "bhejdo", "bhejiye", "karo", "kro", "lagao", "laga",
          "dial", "set", "alarm", "timer", "open", "kholo")
REPLY = _s("reply", "riply", "jawab", "javab", "jawaab", "jawap", "uttar", "respond", "answer")
SENT = _s("diya", "diye", "bheja", "bhejaa", "kiya", "gaya", "gayi")
DO = _s("de", "do", "dena", "dijiye", "kar", "karo", "kro", "kardo", "krdo", "kardena", "bhejo", "bhej", "bhejna",
        "kijiye", "kariye", "send", "dedo", "dedena", "karde")
DO_SENT = _s("de", "do", "dena", "kar", "karo", "kro", "bhejo", "bhej")


def _any(w, s):
    return any(t in s for t in w)


def is_inbox_command(utterance):
    w = jc.words(utterance)
    if not w or len(w) > 24:
        return False
    q = _any(w, QUERY)
    msg = _any(w, MSG)
    call = _any(w, CALL)
    send = _any(w, SEND)
    if _any(w, REPLY):
        if len(w) > 7 or _any(w, _s("ki", "kee", "bolo", "likho", "saying", "that")):
            return False
        if _any(w, SENT) and not _any(w, DO_SENT):
            return True
        if _any(w, SENT) and _any(w, _s("kya", "kisko", "kisne", "kiska", "kitne")):
            return True
        return _any(w, DO)
    if send and not _any(w, _s("kitne", "kiske", "kisne", "kiska", "aaya", "aaye", "aayi")):
        return False
    generic = q and _any(w, _s("aaya", "aaye", "aayi", "aya", "aye", "aai", "mile", "mila")) and \
        _any(w, _s("kuch", "koi", "kisi", "kitne", "kiske", "kisne", "kiska", "kiski"))
    return bool((msg or call) and q) or bool(generic)


def send_to_service(app, text):
    """Java service ko bolo: ye baat sambhalo aur bolkar jawab do."""
    from jnius import autoclass
    Intent = autoclass("android.content.Intent")
    Build = autoclass("android.os.Build$VERSION")
    ctx = app.activity
    intent = Intent()
    intent.setClassName(ctx.getPackageName(), "org.myassistant.myvoiceassistant.JarvisOverlayService")
    intent.setAction("org.myassistant.CMD")
    intent.putExtra("text", str(text))
    if int(Build.SDK_INT) >= 26:
        comp = ctx.startForegroundService(intent)
    else:
        comp = ctx.startService(intent)
    if comp is None:
        raise RuntimeError("JarvisOverlayService manifest me nahi mili")


def install_inbox(app, sender=None):
    """app._jarvis_try_inbox(command) lagata hai. True = service ko de diya."""
    send = sender or (lambda text: send_to_service(app, text))

    def try_inbox(command):
        text = str(command)
        if not is_inbox_command(text):
            return False
        try:
            send(text)
            try:
                app.set_status("Messages dekh raha hoon...")
            except Exception:
                pass
            return True
        except Exception as exc:
            print("inbox forward error:", repr(exc))
            return False

    app._jarvis_try_inbox = try_inbox
    return try_inbox
