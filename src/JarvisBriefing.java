package org.myassistant.myvoiceassistant;

import android.app.AlarmManager;
import android.app.PendingIntent;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.os.Build;
import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.URL;
import java.net.URLEncoder;
import java.text.SimpleDateFormat;
import java.util.Calendar;
import java.util.Date;
import java.util.Locale;
import org.json.JSONArray;
import org.json.JSONObject;

/**
 * Subah ka briefing: samay-tarikh, mausam (Open-Meteo, free, bina key), naye message aur missed call.
 * Roz ek tay samay par apne aap sunane ke liye AlarmManager (setAlarmClock) se Jarvis ko jagata hai.
 */
public final class JarvisBriefing {
    private JarvisBriefing() {
    }

    private static final String PREF = "jarvis_brief";
    private static final int REQ = 7791;
    public static final String SCHED_TEXT = "subah ka briefing";

    private static SharedPreferences sp(Context c) {
        return c.getSharedPreferences(PREF, Context.MODE_PRIVATE);
    }

    // ------------------------------------------------------------------ shehar --
    public static String city(Context c) {
        return sp(c).getString("city", "");
    }

    public static void setCity(Context c, String city) {
        sp(c).edit().putString("city", city.trim()).remove("geo").apply();
    }

    private static String httpGet(String u) {
        HttpURLConnection con = null;
        try {
            con = (HttpURLConnection) new URL(u).openConnection();
            con.setConnectTimeout(6000);
            con.setReadTimeout(7000);
            con.setRequestProperty("User-Agent", "JARVIS-assistant");
            if (con.getResponseCode() != 200) {
                return "";
            }
            BufferedReader r = new BufferedReader(new InputStreamReader(con.getInputStream(), "UTF-8"));
            StringBuilder sb = new StringBuilder();
            String line;
            while ((line = r.readLine()) != null) {
                sb.append(line);
            }
            r.close();
            return sb.toString();
        } catch (Exception e) {
            return "";
        } finally {
            if (con != null) {
                con.disconnect();
            }
        }
    }

    private static String describe(int code) {
        if (code == 0) {
            return "aasmaan saaf hai";
        } else if (code <= 2) {
            return "halke badal hain";
        } else if (code == 3) {
            return "badal chhaye hain";
        } else if (code == 45 || code == 48) {
            return "kohra hai";
        } else if (code >= 51 && code <= 57) {
            return "halki phuhaar hai";
        } else if (code >= 61 && code <= 65) {
            return "baarish ho rahi hai";
        } else if (code == 66 || code == 67) {
            return "thandi baarish hai";
        } else if (code >= 71 && code <= 77) {
            return "baraf gir rahi hai";
        } else if (code >= 80 && code <= 82) {
            return "baarish ki bauchharen hain";
        } else if (code == 85 || code == 86) {
            return "baraf ki bauchharen hain";
        } else if (code >= 95) {
            return "aandhi toofan aur bijli ka mausam hai";
        }
        return "mausam mila-jula hai";
    }

    /** Mausam ka sunane layak vaakya. "" = nahi mil paya. cityArg khaali ho to saved shehar. */
    public static String weather(Context c, String cityArg) {
        String city = cityArg == null || cityArg.trim().length() == 0 ? city(c) : cityArg.trim();
        if (city.length() == 0) {
            return "";
        }
        try {
            double lat, lon;
            String shown = city;
            String geo = sp(c).getString("geo", "");
            boolean useSaved = (cityArg == null || cityArg.trim().length() == 0) && geo.startsWith(city.toLowerCase(Locale.ENGLISH) + "|");
            if (useSaved) {
                String[] p = geo.split("\\|");
                lat = Double.parseDouble(p[1]);
                lon = Double.parseDouble(p[2]);
            } else {
                String g = httpGet("https://geocoding-api.open-meteo.com/v1/search?name=" + URLEncoder.encode(city, "UTF-8")
                        + "&count=1&language=en&format=json");
                if (g.length() == 0) {
                    return "";
                }
                JSONArray res = new JSONObject(g).optJSONArray("results");
                if (res == null || res.length() == 0) {
                    return "NOCITY";
                }
                JSONObject r0 = res.getJSONObject(0);
                lat = r0.getDouble("latitude");
                lon = r0.getDouble("longitude");
                if (cityArg == null || cityArg.trim().length() == 0) {
                    sp(c).edit().putString("geo", city.toLowerCase(Locale.ENGLISH) + "|" + lat + "|" + lon).apply();
                }
            }
            String f = httpGet("https://api.open-meteo.com/v1/forecast?latitude=" + lat + "&longitude=" + lon
                    + "&current=temperature_2m,weather_code&daily=temperature_2m_max,temperature_2m_min,"
                    + "precipitation_probability_max&timezone=auto&forecast_days=1");
            if (f.length() == 0) {
                return "";
            }
            JSONObject j = new JSONObject(f);
            JSONObject cur = j.getJSONObject("current");
            JSONObject day = j.getJSONObject("daily");
            int now = (int) Math.round(cur.getDouble("temperature_2m"));
            int code = cur.optInt("weather_code", 0);
            int hi = (int) Math.round(day.getJSONArray("temperature_2m_max").getDouble(0));
            int lo = (int) Math.round(day.getJSONArray("temperature_2m_min").getDouble(0));
            int rain = day.getJSONArray("precipitation_probability_max").optInt(0, 0);
            StringBuilder sb = new StringBuilder();
            sb.append(shown).append(" me abhi ").append(now).append(" degree hai aur ").append(describe(code)).append(". ");
            sb.append("Aaj ").append(lo).append(" se ").append(hi).append(" degree tak jayega");
            if (rain >= 30) {
                sb.append(", baarish ki sambhavna ").append(rain).append(" percent hai, chhata le jaana");
            }
            sb.append(".");
            return sb.toString();
        } catch (Exception e) {
            return "";
        }
    }

    /** Briefing ka poora text (network ke saath, thread se bulao). */
    public static String compose(Context c) {
        Calendar cal = Calendar.getInstance();
        int h = cal.get(Calendar.HOUR_OF_DAY);
        String greet = h < 12 ? "Good morning" : (h < 17 ? "Good afternoon" : "Good evening");
        StringBuilder sb = new StringBuilder();
        sb.append(greet).append(". Aaj ")
                .append(new SimpleDateFormat("EEEE, d MMMM", Locale.ENGLISH).format(new Date()))
                .append(" hai, abhi ").append(new SimpleDateFormat("h:mm a", Locale.ENGLISH).format(new Date()))
                .append(" baj rahe hain. ");
        String w = weather(c, "");
        if (w.equals("NOCITY")) {
            sb.append("Aapka shehar mujhe mila nahi, bolo mera shehar, aur shehar ka naam, hai. ");
        } else if (w.length() > 0) {
            sb.append(w).append(" ");
        } else if (city(c).length() == 0) {
            sb.append("Mausam batane ke liye bolo mera shehar, aur apne shehar ka naam, hai. ");
        } else {
            sb.append("Mausam abhi nahi mil paya. ");
        }
        try {
            String[] a = JarvisInbox.answer(c, new JarvisInbox.Cmd());
            sb.append(a[0].replace("Jawab de doon?", "").trim()).append(" ");
        } catch (Throwable ignored) {
        }
        String busy = null;
        try {
            busy = JarvisStyle.busyReason(c);
        } catch (Throwable ignored) {
        }
        if (busy != null) {
            sb.append("Busy mode abhi chalu hai. ");
        }
        sb.append("Aapka din shubh ho.");
        return sb.toString().trim();
    }

    // ---------------------------------------------------------------- schedule --
    public static int scheduledMinutes(Context c) {
        return sp(c).getInt("sched_min", -1);
    }

    public static void setSchedule(Context c, int minutes) {
        sp(c).edit().putInt("sched_min", minutes).apply();
        schedule(c);
    }

    public static void cancelSchedule(Context c) {
        sp(c).edit().remove("sched_min").apply();
        try {
            AlarmManager am = (AlarmManager) c.getSystemService(Context.ALARM_SERVICE);
            am.cancel(buildPending(c));
        } catch (Throwable ignored) {
        }
    }

    private static PendingIntent buildPending(Context c) {
        Intent i = new Intent(c, JarvisOverlayService.class);
        i.setAction(JarvisOverlayService.ACTION_CMD);
        i.putExtra("text", SCHED_TEXT);
        i.putExtra("brief_sched", true);
        int fl = PendingIntent.FLAG_UPDATE_CURRENT | (Build.VERSION.SDK_INT >= 23 ? PendingIntent.FLAG_IMMUTABLE : 0);
        if (Build.VERSION.SDK_INT >= 26) {
            return PendingIntent.getForegroundService(c, REQ, i, fl);
        }
        return PendingIntent.getService(c, REQ, i, fl);
    }

    /** Agli baar ka alarm lagao (roz ke liye har baar dobara). Schedule band ho to kuch nahi. */
    public static void schedule(Context c) {
        try {
            int m = scheduledMinutes(c);
            if (m < 0) {
                return;
            }
            Calendar t = Calendar.getInstance();
            t.set(Calendar.HOUR_OF_DAY, m / 60);
            t.set(Calendar.MINUTE, m % 60);
            t.set(Calendar.SECOND, 0);
            t.set(Calendar.MILLISECOND, 0);
            if (t.getTimeInMillis() <= System.currentTimeMillis() + 30000L) {
                t.add(Calendar.DAY_OF_MONTH, 1);
            }
            AlarmManager am = (AlarmManager) c.getSystemService(Context.ALARM_SERVICE);
            Intent launch = c.getPackageManager().getLaunchIntentForPackage(c.getPackageName());
            int fl = PendingIntent.FLAG_UPDATE_CURRENT | (Build.VERSION.SDK_INT >= 23 ? PendingIntent.FLAG_IMMUTABLE : 0);
            PendingIntent show = PendingIntent.getActivity(c, REQ + 1, launch != null ? launch : new Intent(), fl);
            am.setAlarmClock(new AlarmManager.AlarmClockInfo(t.getTimeInMillis(), show), buildPending(c));
        } catch (Throwable ignored) {
        }
    }

    public static String shownTime(int minutes) {
        Calendar t = Calendar.getInstance();
        t.set(Calendar.HOUR_OF_DAY, minutes / 60);
        t.set(Calendar.MINUTE, minutes % 60);
        return new SimpleDateFormat("h:mm a", Locale.ENGLISH).format(t.getTime());
    }
}
