[app]

title = My Voice Assistant
package.name = myvoiceassistant
package.domain = org.myassistant

source.dir = .
source.include_exts = py,png,jpg,kv,atlas,java,xml

version = 0.1

requirements = python3,kivy,pyjnius

orientation = portrait
fullscreen = 0

android.permissions = android.permission.RECORD_AUDIO,com.android.alarm.permission.SET_ALARM,android.permission.POST_NOTIFICATIONS,android.permission.VIBRATE,android.permission.SCHEDULE_EXACT_ALARM

android.api = 33
android.minapi = 21
android.archs = arm64-v8a
android.accept_sdk_license = True

android.add_src = src
android.extra_manifest_application_arguments = src/extra_manifest_application.xml

p4a.branch = master

[buildozer]

log_level = 2
warn_on_root = 1
