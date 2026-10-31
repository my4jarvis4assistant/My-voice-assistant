"""python-for-android hook: Jarvis ke Java components ko AndroidManifest me jodta hai.

Kyun: buildozer ki 'android.extra_manifest_application_xml' key bahut nayi hai aur
aapke build me kaam nahi karti thi, isliye JarvisOverlayService / JarvisTriggerActivity /
JarvisTileService / JarvisAlarmReceiver manifest me jude hi nahi.
Ye hook APK banne se theek pehle manifest ko khud patch kar deta hai. Agar kisi
component ka naam manifest me pehle se hai to dobara nahi jodta (duplicate nahi hota).

buildozer.spec me:   p4a.hook = p4a_hook.py
"""
import glob
import os

PKG = "org.myassistant.myvoiceassistant"

# (naam, xml)
COMPONENTS = [
    ("JarvisAlarmReceiver", """
        <receiver
            android:name="%(p)s.JarvisAlarmReceiver"
            android:enabled="true"
            android:exported="false" />
""" ),
    ("JarvisOverlayService", """
        <service
            android:name="%(p)s.JarvisOverlayService"
            android:exported="false"
            android:foregroundServiceType="microphone" />
"""),
    ("JarvisTriggerActivity", """
        <activity
            android:name="%(p)s.JarvisTriggerActivity"
            android:theme="@android:style/Theme.Translucent.NoTitleBar"
            android:excludeFromRecents="true"
            android:noHistory="true"
            android:taskAffinity=""
            android:exported="true" />
"""),
    ("JarvisTileService", """
        <service
            android:name="%(p)s.JarvisTileService"
            android:label="Jarvis"
            android:icon="@android:drawable/ic_btn_speak_now"
            android:permission="android.permission.BIND_QUICK_SETTINGS_TILE"
            android:exported="true">
            <intent-filter>
                <action android:name="android.service.quicksettings.action.QS_TILE" />
            </intent-filter>
        </service>
"""),
]


ACCESS_COMPONENT = ("JarvisAccessService", """
        <service
            android:name="%(p)s.JarvisAccessService"
            android:label="JARVIS auto-send"
            android:permission="android.permission.BIND_ACCESSIBILITY_SERVICE"
            android:exported="true">
            <intent-filter>
                <action android:name="android.accessibilityservice.AccessibilityService" />
            </intent-filter>
            <meta-data
                android:name="android.accessibilityservice"
                android:resource="@xml/jarvis_access" />
        </service>
""")

ACCESS_XML = """<?xml version="1.0" encoding="utf-8"?>
<accessibility-service xmlns:android="http://schemas.android.com/apk/res/android"
    android:accessibilityEventTypes="typeWindowStateChanged|typeWindowContentChanged"
    android:accessibilityFeedbackType="feedbackGeneric"
    android:accessibilityFlags="flagReportViewIds|flagRetrieveInteractiveWindows"
    android:canRetrieveWindowContent="true"
    android:notificationTimeout="150"
    android:packageNames="com.whatsapp,com.whatsapp.w4b" />
"""


def write_access_resource(manifest_path):
    """res/xml/jarvis_access.xml likho (manifest ke bagal). Kamyab ho to True."""
    try:
        res_dir = os.path.join(os.path.dirname(manifest_path), "res", "xml")
        os.makedirs(res_dir, exist_ok=True)
        with open(os.path.join(res_dir, "jarvis_access.xml"), "w", encoding="utf-8") as fh:
            fh.write(ACCESS_XML)
        return True
    except Exception as exc:
        print("[jarvis-hook] access resource nahi bana:", exc)
        return False


def patch_manifest_text(text, pkg=PKG, access=False):
    """Manifest text me jo components nahi hain unhe </application> se pehle jodta hai."""
    added = []
    block = ""
    comps = list(COMPONENTS) + ([ACCESS_COMPONENT] if access else [])
    for name, xml in comps:
        if (pkg + "." + name) in text or ('"' + "." + name + '"') in text:
            continue
        block += xml % {"p": pkg}
        added.append(name)
    if not block:
        return text, added
    idx = text.rfind("</application>")
    if idx < 0:
        raise RuntimeError("</application> nahi mila")
    return text[:idx] + block + "    " + text[idx:], added


def _find_manifests(toolchain):
    roots = []
    try:
        dist = getattr(toolchain, "_dist", None)
        if dist is not None and getattr(dist, "dist_dir", None):
            roots.append(dist.dist_dir)
    except Exception:
        pass
    roots.append(os.getcwd())
    found = []
    for root in roots:
        for pat in ("src/main/AndroidManifest.xml", "AndroidManifest.xml"):
            p = os.path.join(root, pat)
            if os.path.isfile(p) and p not in found:
                found.append(p)
    return found


def _patch(toolchain, when):
    try:
        _patch_inner(toolchain, when)
    except Exception as exc:          # build ko kabhi na todo; galti log me dikhegi
        import traceback
        print("[jarvis-hook] (%s) GALTI: %r" % (when, exc))
        traceback.print_exc()


def _patch_inner(toolchain, when):
    manifests = _find_manifests(toolchain)
    if not manifests:
        print("[jarvis-hook] (%s) AndroidManifest.xml nahi mila" % when)
        return
    for path in manifests:
        with open(path, "r", encoding="utf-8") as fh:
            text = fh.read()
        access_ok = write_access_resource(path)
        new, added = patch_manifest_text(text, access=access_ok)
        if added:
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(new)
            print("[jarvis-hook] (%s) %s me joda gaya: %s" % (when, path, ", ".join(added)))
        else:
            print("[jarvis-hook] (%s) %s me sab components pehle se hain" % (when, path))


def after_apk_build(toolchain):
    _patch(toolchain, "after_apk_build")


def before_apk_assemble(toolchain):
    _patch(toolchain, "before_apk_assemble")
