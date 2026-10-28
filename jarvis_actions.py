"""JARVIS actions fix (alarm, timer, reminder) - main.py ko bina badle.

Kya badla:
  * Alarm / timer ab phone ki asli Clock app se lagte hain (AlarmClock intent), jo hamesha
    bajti hai. Pehle wala AlarmManager+receiver tareeka Android/MIUI me chup-chaap fail ho jata tha.
  * Reminder ka naam (title) ab Calendar form me sahi type (java String) me bheja jata hai
    aur Hinglish command se naam behtar nikala jata hai.
install_actions(app) in teen methods ko app par badal deta hai. Koi galti ho to purane
methods ya error message wapas aa jate hain, app band nahi hota.
"""
import re
from datetime import datetime, timedelta


# ------------------------------------------------------------- parsing ----
_TIME_AMPM = re.compile(r"\b(\d{1,2})(?:[:.](\d{2}))?\s*([ap])\.?\s?m\b\.?", re.I)
_TIME_COLON = re.compile(r"\b(\d{1,2}):(\d{2})\b")
_TIME_BAJE = re.compile(r"\b(\d{1,2})(?:[:.](\d{2}))?\s*baje\b", re.I)
_EVENING = ("shaam", "sham", "raat", "evening", "night", "dopahar", "afternoon")
_MORNING = ("subah", "morning", "savere")

_STRIP = [
    r"\bjarvis\b", r"\bplease\b", r"\bremind me to\b", r"\bremind me\b", r"\bremind\b",
    r"\breminder (?:set )?(?:karo|kar do|lagao|laga do|banao|bana do)\b", r"\breminder\b",
    r"\bset (?:karo|kar do)\b", r"\bset a\b", r"\byaad dila(?:na|o| do)\b", r"\bmujhe\b",
    r"\bday after tomorrow\b", r"\bparso\b", r"\btomorrow\b", r"\btoday\b", r"\bkal\b", r"\baaj\b",
    r"\bsubah\b", r"\bshaam\b", r"\bsham\b", r"\braat\b", r"\bdopahar\b", r"\bmorning\b",
    r"\bevening\b", r"\bnight\b", r"\bafternoon\b", r"\bbaje\b", r"\bat\b", r"\bon\b",
    r"\bke liye\b", r"\bfor me\b", r"\bto\b(?=\s|$)",
]


def _to_24h(hour, minute, period, text):
    if period == "pm" and hour < 12:
        hour += 12
    elif period == "am" and hour == 12:
        hour = 0
    elif not period:
        if any(w in text for w in _EVENING) and hour < 12:
            hour = hour + 12 if not ("dopahar" in text and hour == 12) else 12
        elif any(w in text for w in _MORNING) and hour == 12:
            hour = 0
    return hour, minute


def parse_time(text):
    """Text me se (hour24, minute) nikalo, na mile to None."""
    t = text.lower()
    m = _TIME_AMPM.search(t)
    if m:
        h, mi, per = int(m.group(1)), int(m.group(2) or 0), m.group(3).lower() + "m"
        h, mi = _to_24h(h, mi, per, t)
    else:
        m = _TIME_COLON.search(t) or _TIME_BAJE.search(t)
        if not m:
            return None
        h, mi = int(m.group(1)), int(m.group(2) or 0)
        h, mi = _to_24h(h, mi, "", t)
    if 0 <= h <= 23 and 0 <= mi <= 59:
        return h, mi
    return None


def parse_reminder(command, now=None):
    """(title, datetime) - command se reminder ka naam aur samay."""
    now = now or datetime.now()
    c = " ".join(str(command).lower().split())
    days = 0
    if "day after tomorrow" in c or re.search(r"\bparso\b", c):
        days = 2
    elif re.search(r"\b(?:tomorrow|kal)\b", c):
        days = 1
    tm = parse_time(c)
    if tm:
        target = datetime.combine((now + timedelta(days=days)).date(), datetime.min.time())
        target = target.replace(hour=tm[0], minute=tm[1])
        if target <= now and days == 0:
            target += timedelta(days=1)
    elif days:
        target = (now + timedelta(days=days)).replace(hour=9, minute=0, second=0, microsecond=0)
    else:
        target = (now + timedelta(hours=1)).replace(second=0, microsecond=0)
    title = c
    title = _TIME_AMPM.sub(" ", title)
    title = _TIME_COLON.sub(" ", title)
    title = _TIME_BAJE.sub(" ", title)
    for pat in _STRIP:
        title = re.sub(pat, " ", title)
    title = re.sub(r"[^\w\sऀ-ॿ'&-]", " ", title)
    title = re.sub(r"\s+", " ", title).strip(" ,.-")
    title = (title[:1].upper() + title[1:]) if title else "JARVIS Reminder"
    return title, target


def pretty_clock(hour, minute):
    h12 = hour % 12 or 12
    return "%d:%02d %s" % (h12, minute, "AM" if hour < 12 else "PM")


def pretty_duration(seconds):
    seconds = int(seconds)
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    parts = []
    if h:
        parts.append("%d ghanta" % h)
    if m:
        parts.append("%d minute" % m)
    if s and not h:
        parts.append("%d second" % s)
    return " ".join(parts) or "0 second"


# --------------------------------------------------------------- install ---
def install_actions(app):
    from kivy.clock import Clock
    from jnius import autoclass

    Intent = autoclass("android.content.Intent")
    AlarmClock = autoclass("android.provider.AlarmClock")
    JString = autoclass("java.lang.String")

    orig_alarm = getattr(app, "_schedule_android_alarm", None)
    orig_timer = getattr(app, "_schedule_android_timer", None)
    orig_reminder = getattr(app, "create_calendar_reminder", None)

    def say(text):
        try:
            app.set_status(text)
            app.speak(text)
        except Exception as exc:
            print("say error:", exc)

    def relisten():
        try:
            Clock.schedule_once(lambda dt: app.listen(), 2.5)
        except Exception:
            pass

    Bundle = autoclass("android.os.Bundle")

    def typed_extras(ints=None, strings=None, bools=None):
        """putExtra ke overloads me pyjnius galat type chun leta hai (Clock app ko 0/current time
        milta tha). Bundle.putInt/putString/putBoolean ke naam alag hain, isliye type pakka rehta hai."""
        b = Bundle()
        for k, v in (ints or {}).items():
            b.putInt(k, int(v))
        for k, v in (strings or {}).items():
            b.putString(k, str(v))
        for k, v in (bools or {}).items():
            b.putBoolean(k, bool(v))
        return b

    def start(intent):
        intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        app.activity.startActivity(intent)

    def schedule_alarm(hour, minute):
        def run():
            try:
                hour_i, minute_i = int(hour), int(minute)
                if not (0 <= hour_i <= 23 and 0 <= minute_i <= 59):
                    raise ValueError("Invalid alarm time")
                intent = Intent(AlarmClock.ACTION_SET_ALARM)
                intent.putExtras(typed_extras(
                    ints={AlarmClock.EXTRA_HOUR: hour_i, AlarmClock.EXTRA_MINUTES: minute_i},
                    strings={AlarmClock.EXTRA_MESSAGE: "JARVIS"},
                    bools={AlarmClock.EXTRA_SKIP_UI: True}))
                start(intent)
                when = pretty_clock(hour_i, minute_i)
                say("Alarm " + when + " ke liye set ho gaya.")
                print("JARVIS CLOCK ALARM:", when)
            except Exception as exc:
                print("JARVIS CLOCK ALARM ERROR:", repr(exc))
                if orig_alarm is not None:
                    orig_alarm(hour, minute)
                else:
                    say("Alarm set nahi ho paya.")
            relisten()
        app.run_on_android_thread(run)

    def schedule_timer(seconds):
        def run():
            try:
                secs = int(seconds)
                if secs <= 0 or secs > 86400:
                    raise ValueError("Timer must be between 1 and 86400 seconds")
                intent = Intent(AlarmClock.ACTION_SET_TIMER)
                intent.putExtras(typed_extras(
                    ints={AlarmClock.EXTRA_LENGTH: secs},
                    strings={AlarmClock.EXTRA_MESSAGE: "JARVIS"},
                    bools={AlarmClock.EXTRA_SKIP_UI: True}))
                start(intent)
                say("Timer " + pretty_duration(secs) + " ke liye start ho gaya.")
                print("JARVIS CLOCK TIMER:", secs)
            except Exception as exc:
                print("JARVIS CLOCK TIMER ERROR:", repr(exc))
                if orig_timer is not None:
                    orig_timer(seconds)
                else:
                    say("Timer start nahi ho paya.")
            relisten()
        app.run_on_android_thread(run)

    def create_reminder(command):
        try:
            title, target = parse_reminder(command)
            begin_ms = int(target.timestamp() * 1000)
            end_ms = begin_ms + 30 * 60 * 1000
            Events = autoclass("android.provider.CalendarContract$Events")
            CalendarContract = autoclass("android.provider.CalendarContract")
            intent = Intent(Intent.ACTION_INSERT)
            intent.setData(Events.CONTENT_URI)
            jtitle = JString(title)
            intent.putExtra(Events.TITLE, jtitle)
            intent.putExtra("android.intent.extra.TITLE", jtitle)
            intent.putExtra(Events.DESCRIPTION, JString("JARVIS reminder: " + title))
            intent.putExtra(CalendarContract.EXTRA_EVENT_BEGIN_TIME, begin_ms)
            intent.putExtra(CalendarContract.EXTRA_EVENT_END_TIME, end_ms)
            start(intent)
            when = target.strftime("%d %b, %I:%M %p")
            say("Reminder: " + title + ", " + when + ". Calendar me Save dabaiye.")
            print("JARVIS REMINDER:", title, target.isoformat())
        except Exception as exc:
            print("JARVIS REMINDER ERROR:", repr(exc))
            if orig_reminder is not None:
                orig_reminder(command)
            else:
                say("Reminder editor nahi khul saka.")

    app._schedule_android_alarm = schedule_alarm
    app._schedule_android_timer = schedule_timer
    app.create_calendar_reminder = create_reminder
    print("JARVIS actions installed (clock alarm/timer, reminder title)")


def normalize_alarm_command(command):
    """main.py ka alarm parser 'am/pm' tokens hi samajhta hai: a.m., shaam waghera ko usme badlo."""
    c = str(command)
    low = c.lower()
    if "alarm" not in low:
        return c
    c = re.sub(r"\b([ap])\.\s?m\.?", lambda m: m.group(1).lower() + "m", c, flags=re.I)
    low = c.lower()
    if not re.search(r"\b(?:am|pm)\b", low):
        if any(w in low for w in ("shaam", "sham", "dopahar", "evening", "afternoon")):
            c += " pm"
        elif any(w in low for w in ("subah", "morning", "savere")):
            c += " am"
    return c
