"""Build ke waqt (GitHub Actions me) chalti hai: GitHub Secrets se jarvis_secrets.py banati hai.

Keys repo me kabhi nahi likhi jaati; ye file sirf build ke dauran banti hai aur APK ke andar jati hai.
Isse app delete karke dobara install karne par bhi keys apne aap wapas mil jati hain.

Secrets (sab optional):
  GEMINI_KEY, CONVERSATION_KEY, ELEVEN_KEY
  ELEVEN_VOICES   ->  har line ya comma par  Naam=VoiceID   (7 tak), jaise:
                      Priya=21m00Tcm4TlvDq8ikWAM
                      Raj=AZnzlk1XvdvUeBnXmlld
"""
import os
import re


def parse_voices(text):
    out = []
    for part in re.split(r"[\n,;]+", text or ""):
        if "=" not in part:
            continue
        name, vid = part.split("=", 1)
        name, vid = name.strip(), vid.strip()
        if name and vid:
            out.append([name, vid])
    return out[:7]


def build_source(env):
    lines = ['"""Auto-generated at build time. Do not commit."""']
    for var in ("GEMINI_KEY", "CONVERSATION_KEY", "ELEVEN_KEY"):
        lines.append("%s = %r" % (var, (env.get(var) or "").strip()))
    lines.append("ELEVEN_VOICES = %r" % (parse_voices(env.get("ELEVEN_VOICES", "")),))
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    src = build_source(os.environ)
    with open("jarvis_secrets.py", "w", encoding="utf-8") as fh:
        fh.write(src)
    found = [v for v in ("GEMINI_KEY", "CONVERSATION_KEY", "ELEVEN_KEY", "ELEVEN_VOICES") if os.environ.get(v)]
    print("jarvis_secrets.py bani. Mili secrets:", ", ".join(found) or "koi nahi")
