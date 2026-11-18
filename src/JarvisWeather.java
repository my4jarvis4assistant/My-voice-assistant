package org.myassistant.myvoiceassistant;

import android.content.Context;
import android.content.pm.PackageManager;
import android.location.Location;
import android.location.LocationManager;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.URL;
import java.util.List;

/** Aap jahan ho wahan ka mausam: GPS/network location se, na mile to IP se (shehar ke level tak). */
public final class JarvisWeather {
    private JarvisWeather() {
    }

    private static String get(String url) throws Exception {
        HttpURLConnection c = (HttpURLConnection) new URL(url).openConnection();
        try {
            c.setConnectTimeout(10000);
            c.setReadTimeout(15000);
            c.setRequestProperty("User-Agent", "JARVIS/1.0");
            if (c.getResponseCode() >= 400) {
                throw new Exception("HTTP " + c.getResponseCode());
            }
            BufferedReader br = new BufferedReader(new InputStreamReader(c.getInputStream(), "UTF-8"));
            StringBuilder sb = new StringBuilder();
            String line;
            while ((line = br.readLine()) != null) {
                sb.append(line);
            }
            br.close();
            return sb.toString();
        } finally {
            c.disconnect();
        }
    }

    private static double[] deviceLocation(Context ctx) {
        try {
            boolean ok = ctx.checkSelfPermission("android.permission.ACCESS_COARSE_LOCATION") == PackageManager.PERMISSION_GRANTED
                    || ctx.checkSelfPermission("android.permission.ACCESS_FINE_LOCATION") == PackageManager.PERMISSION_GRANTED;
            if (!ok) {
                return null;
            }
            LocationManager lm = (LocationManager) ctx.getSystemService(Context.LOCATION_SERVICE);
            Location best = null;
            List<String> ps = lm.getAllProviders();
            for (String p : ps) {
                try {
                    Location l = lm.getLastKnownLocation(p);
                    if (l != null && (best == null || l.getTime() > best.getTime())) {
                        best = l;
                    }
                } catch (Throwable ignored) {
                }
            }
            if (best != null && System.currentTimeMillis() - best.getTime() < 6L * 3600L * 1000L) {
                return new double[]{best.getLatitude(), best.getLongitude()};
            }
        } catch (Throwable ignored) {
        }
        return null;
    }

    private static String cityOf(double lat, double lon) {
        try {
            JSONObject o = new JSONObject(get("https://api.bigdatacloud.net/data/reverse-geocode-client?latitude="
                    + lat + "&longitude=" + lon + "&localityLanguage=en"));
            String c = o.optString("locality", "");
            if (c.length() == 0) {
                c = o.optString("city", "");
            }
            return c;
        } catch (Throwable t) {
            return "";
        }
    }

    private static String describe(int code) {
        if (code == 0) return "aasmaan saaf hai";
        if (code == 1) return "zyadatar saaf aasmaan";
        if (code == 2) return "thode baadal";
        if (code == 3) return "baadal chhaye hain";
        if (code == 45 || code == 48) return "kohra hai";
        if (code >= 51 && code <= 57) return "halki phuhaar";
        if (code >= 61 && code <= 65) return code == 65 ? "tez barish" : "barish";
        if (code == 66 || code == 67) return "barf jaisi barish";
        if (code >= 71 && code <= 77) return "barfbari";
        if (code >= 80 && code <= 82) return "barish ki bauchhar";
        if (code == 85 || code == 86) return "barfbari ki bauchhar";
        if (code >= 95) return "toofan aur bijli";
        return "mausam badalta hua";
    }

    /** Blocking: network wale thread me chalao. tomorrow=true to kal ka mausam. */
    public static String fetch(Context ctx, boolean tomorrow) throws Exception {
        double lat, lon;
        String city = "";
        double[] loc = deviceLocation(ctx);
        if (loc != null) {
            lat = loc[0];
            lon = loc[1];
            city = cityOf(lat, lon);
        } else {
            JSONObject ip = null;
            try {
                ip = new JSONObject(get("https://ipwho.is/"));
                if (!ip.optBoolean("success", true)) {
                    ip = null;
                }
            } catch (Throwable t) {
                ip = null;
            }
            if (ip == null) {
                ip = new JSONObject(get("https://ipapi.co/json/"));
            }
            lat = ip.getDouble("latitude");
            lon = ip.getDouble("longitude");
            city = ip.optString("city", "");
        }
        JSONObject o = new JSONObject(get("https://api.open-meteo.com/v1/forecast?latitude=" + lat + "&longitude=" + lon
                + "&current=temperature_2m,relative_humidity_2m,apparent_temperature,weather_code,wind_speed_10m"
                + "&daily=temperature_2m_max,temperature_2m_min,precipitation_probability_max,weather_code"
                + "&timezone=auto&forecast_days=2"));
        JSONObject cur = o.getJSONObject("current");
        JSONObject day = o.getJSONObject("daily");
        int idx = tomorrow ? 1 : 0;
        int mx = (int) Math.round(day.getJSONArray("temperature_2m_max").getDouble(idx));
        int mn = (int) Math.round(day.getJSONArray("temperature_2m_min").getDouble(idx));
        JSONArray pr = day.optJSONArray("precipitation_probability_max");
        int rain = pr == null || pr.isNull(idx) ? -1 : pr.getInt(idx);
        String where = city.length() > 0 ? city + " me" : "Aapki location par";
        StringBuilder sb = new StringBuilder();
        if (tomorrow) {
            sb.append("Kal ").append(where.replace(" me", "")).append(" me ")
                    .append(describe(day.getJSONArray("weather_code").getInt(1)))
                    .append(", taapmaan ").append(mn).append(" se ").append(mx).append(" degree rahega.");
        } else {
            int t = (int) Math.round(cur.getDouble("temperature_2m"));
            int f = (int) Math.round(cur.getDouble("apparent_temperature"));
            int h = (int) Math.round(cur.getDouble("relative_humidity_2m"));
            int w = (int) Math.round(cur.getDouble("wind_speed_10m"));
            sb.append(where).append(" abhi ").append(t).append(" degree hai, ").append(describe(cur.getInt("weather_code")))
                    .append(". Mehsoos ").append(f).append(" degree jaisa ho raha hai. Nami ").append(h)
                    .append(" percent aur hawa ").append(w).append(" kilometre per ghanta.")
                    .append(" Aaj ka taapmaan ").append(mn).append(" se ").append(mx).append(" degree rahega.");
        }
        if (rain >= 0) {
            sb.append(" Barish ki sambhavna ").append(rain).append(" percent.");
        }
        if (loc == null) {
            sb.append(" Sahi location ke liye Jarvis ko location ki permission de do.");
        }
        return sb.toString();
    }
}
