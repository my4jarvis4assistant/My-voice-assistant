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

# Microphone permission
android.permissions = android.permission.RECORD_AUDIO

# Android settings
android.api = 33
android.min_api = 21
android.sdk = 33
android.arch = arm64-v8a

[buildozer]

log_level = 2

warn_on_root = 1

