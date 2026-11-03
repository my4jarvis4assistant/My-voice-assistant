"""JARVIS: Voice-Access jaisa control (click, scroll, type, send, back...) app ke andar bole gaye tukde ke liye.

Samajhna Java (JarvisControl) karta hai, asli kaam Accessibility service. Yahan sirf: agar ye control ka kaam hai
to Java service ko bhej do (wahi screen par kaam karti hai aur sunti rehti hai).
"""


def is_control(text):
    from jnius import autoclass
    return bool(autoclass("org.myassistant.myvoiceassistant.JarvisControl").isControl(str(text)))


def install_control(app, checker=None, sender=None):
    """app._jarvis_try_control(command) lagata hai. True = service ko de diya."""
    import jarvis_inbox as ji
    check = checker or is_control
    send = sender or (lambda t: ji.send_to_service(app, t))

    def try_control(command):
        text = str(command)
        st = getattr(app, "_jarvis_social_state", None) or {}
        if st.get("confirm") or st.get("await_body") or st.get("await_name") or st.get("choices") is not None:
            return False                               # WhatsApp baat-cheet chal rahi hai: "haan/send" wahin ka hai
        try:
            if not check(text):
                return False
            send(text)
            try:
                app.set_status("Kar raha hoon...")
            except Exception:
                pass
            return True
        except Exception as exc:
            print("control forward error:", repr(exc))
            return False

    app._jarvis_try_control = try_control
    return try_control
