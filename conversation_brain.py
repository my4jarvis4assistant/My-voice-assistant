"""JARVIS natural conversation client."""
import json
import urllib.error
import urllib.request

DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_MODEL = "openrouter/free"
MAX_HISTORY_MESSAGES = 12
MAX_HISTORY_CHARS = 9000


class ConversationError(Exception):
    def __init__(self, kind, detail=""):
        super().__init__(kind)
        self.kind = kind
        self.detail = detail

    @property
    def message(self):
        messages = {
            "nokey": "AI API key set nahi hai. Pehle key configure karein.",
            "quota": "AI service ki limit poori hai. Baad mein dobara koshish karein.",
            "auth": "API key accept nahi hui. Key aur permission check karein.",
            "network": "Internet connection check karke dobara koshish karein.",
            "busy": "AI service abhi busy hai. Thodi der baad koshish karein.",
            "empty": "AI se khaali jawab mila. Dobara poochhein.",
            "other": "AI se baat karte waqt error hua. Dobara koshish karein.",
        }
        return messages.get(self.kind, messages["other"])


def _http_post(url, headers, payload, timeout=45):
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")

    try:
        from jnius import autoclass, cast

        URL = autoclass("java.net.URL")
        BufferedReader = autoclass("java.io.BufferedReader")
        InputStreamReader = autoclass("java.io.InputStreamReader")

        conn = cast(
            "java.net.HttpURLConnection",
            URL(url).openConnection()
        )

        try:
            conn.setRequestMethod("POST")
            conn.setConnectTimeout(15000)
            conn.setReadTimeout(timeout * 1000)
            conn.setDoOutput(True)

            for name, value in headers.items():
                conn.setRequestProperty(name, value)

            output = conn.getOutputStream()
            output.write(body)
            output.flush()
            output.close()

            status = int(conn.getResponseCode())
            stream = (
                conn.getInputStream()
                if status < 400
                else conn.getErrorStream()
            )

            if stream is None:
                response = ""
            else:
                reader = BufferedReader(
                    InputStreamReader(stream, "UTF-8")
                )
                lines = []

                while True:
                    line = reader.readLine()
                    if line is None:
                        break
                    lines.append(str(line))

                reader.close()
                response = "\n".join(lines)

            return status, response

        finally:
            conn.disconnect()

    except ImportError:
        pass
    except Exception as exc:
        detail = str(exc).lower()

        if any(word in detail for word in (
            "unknownhost", "connectexception", "timeout",
            "sslhandshake", "network is unreachable"
        )):
            raise ConversationError("network", str(exc))

        raise ConversationError("other", str(exc))

    request = urllib.request.Request(
        url,
        data=body,
        headers=headers,
        method="POST"
    )

    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return (
                response.status,
                response.read().decode("utf-8", "replace")
            )

    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", "replace")

    except Exception as exc:
        raise ConversationError("network", str(exc))


class ConversationClient:
    def __init__(
        self,
        get_key,
        get_verbosity=lambda: "Balanced",
        base_url=DEFAULT_BASE_URL,
        model=DEFAULT_MODEL,
        app_name="JARVIS Voice Assistant"
    ):
        self.get_key = get_key
        self.get_verbosity = get_verbosity
        self.base_url = (base_url or DEFAULT_BASE_URL).rstrip("/")
        self.model = model or DEFAULT_MODEL
        self.app_name = app_name
        self.history = []
        self.last_detail = ""

    def clear(self):
        self.history = []

    def _trim(self):
        self.history = self.history[-MAX_HISTORY_MESSAGES:]

        while (
            len(self.history) > 2
            and sum(
                len(str(item.get("content", "")))
                for item in self.history
            ) > MAX_HISTORY_CHARS
        ):
            self.history = self.history[2:]

    def _system_prompt(self):
        verbosity = str(self.get_verbosity() or "Balanced")

        length = {
            "Concise": "Aam taur par 1-2 vaakyon mein jawab do.",
            "Balanced": "Aam taur par 2-4 vaakya; zaroorat par detail do.",
            "Detailed": "Zaroorat par detail aur step-by-step samjhao."
        }.get(
            verbosity,
            "Aam taur par 2-4 vaakya; zaroorat par detail do."
        )

        return (
            "Tum JARVIS ho, ek helpful Android voice assistant. "
            "Natural Hindi/Hinglish mein baat karo aur user ki "
            "language ke hisaab se jawab do. Har jawab ek jaisa "
            "mat banao. Context yaad rakho aur pichhli baaton ka "
            "sahi istemal karo. Jo baat yaad nahi hai uska jhootha "
            "daawa mat karo. Phone par koi action hua hai, iska "
            "daawa tabhi karo jab app uski success confirm kare. "
            + length
        )

    def ask(self, user_text):
        """Blocking call: returns (success, reply_or_error)."""
        user_text = " ".join(str(user_text).split()).strip()

        if not user_text:
            return False, "Kuchh sunai nahi diya. Dobara boliye."

        key = str(self.get_key() or "").strip()

        if not key:
            return False, ConversationError("nokey").message

        messages = [{
            "role": "system",
            "content": self._system_prompt()
        }]

        messages.extend(self.history)
        messages.append({
            "role": "user",
            "content": user_text
        })

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.8,
            "max_tokens": 500
        }

        headers = {
            "Authorization": "Bearer " + key,
            "Content-Type": "application/json",
            "HTTP-Referer": "https://openrouter.ai/",
            "X-Title": self.app_name
        }

        try:
            status, body = _http_post(
                self.base_url + "/chat/completions",
                headers,
                payload
            )

            try:
                data = json.loads(body or "{}")
            except ValueError:
                data = {}

            if status in (401, 403):
                raise ConversationError("auth", body[:300])

            if status == 429:
                raise ConversationError("quota", body[:300])

            if status >= 500:
                raise ConversationError("busy", body[:300])

            if status >= 400:
                detail = str(
                    data.get("error", {}).get("message", body)
                )[:300]
                raise ConversationError("other", detail)

            choices = data.get("choices") or []
            reply = ""

            if choices:
                message = choices[0].get("message") or {}
                reply = str(message.get("content") or "").strip()

            if not reply:
                raise ConversationError("empty", body[:300])

            self.history.extend([
                {"role": "user", "content": user_text},
                {"role": "assistant", "content": reply}
            ])

            self._trim()
            self.last_detail = ""
            return True, reply

        except ConversationError as exc:
            self.last_detail = exc.detail
            return False, exc.message

        except Exception as exc:
            self.last_detail = repr(exc)[:300]
            return False, ConversationError("other").message
