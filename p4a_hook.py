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


def patch_manifest_text(text, pkg=PKG):
    """Manifest text me jo components nahi hain unhe </application> se pehle jodta hai."""
    added = []
    block = ""
    for name, xml in COMPONENTS:
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
        new, added = patch_manifest_text(text)
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
