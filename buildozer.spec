[app]

title = My Voice Assistant
package.name = myvoiceassistant
package.domain = org.myassistant

source.dir = .
source.include_exts = py,png,jpg,kv,atlas

version = 0.1

requirements = python3,kivy,pyjnius

orientation = portrait
fullscreen = 0

android.permissions = android.permission.RECORD_AUDIO

android.api = 33
android.minapi = 21
android.archs = arm64-v8a

android.accept_sdk_license = True

# Python-for-Android
p4a.branch = master

[buildozer]

log_level = 2
warn_on_root = 1
