[app]

title = My Voice Assistant
package.name = myvoiceassistant
package.domain = org.myassistant

source.dir = .
source.include_exts = py,png,jpg,kv,atlas,java,xml

version = 0.24

requirements = python3,kivy,pyjnius

orientation = portrait
fullscreen = 0

android.permissions = android.permission.RECORD_AUDIO,com.android.alarm.permission.SET_ALARM,android.permission.POST_NOTIFICATIONS,android.permission.VIBRATE,android.permission.SCHEDULE_EXACT_ALARM,android.permission.INTERNET,android.permission.SYSTEM_ALERT_WINDOW,android.permission.FOREGROUND_SERVICE,android.permission.FOREGROUND_SERVICE_MICROPHONE,android.permission.QUERY_ALL_PACKAGES,android.permission.READ_CONTACTS,android.permission.CALL_PHONE

android.api = 33
android.minapi = 21
android.archs = arm64-v8a

android.accept_sdk_license = True

android.add_src = src
android.extra_manifest_application_xml = src/extra_manifest_application.xml

# "Hey Jarvis" wake word (Vosk, offline)
android.gradle_dependencies = net.java.dev.jna:jna:5.13.0@aar,com.alphacephei:vosk-android:0.3.47@aar
android.enable_androidx = True

p4a.branch = master

[buildozer]

log_level = 2
warn_on_root = 1
