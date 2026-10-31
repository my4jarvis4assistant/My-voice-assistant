package org.myassistant.myvoiceassistant;

import android.content.Context;
import android.content.Intent;
import android.database.Cursor;
import android.net.Uri;
import android.provider.ContactsContract;

import java.net.URLEncoder;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/** WhatsApp ke contacts dhoondhna aur unhe call / message ke liye kholna. */
public final class JarvisWhatsApp {
    private JarvisWhatsApp() {
    }

    static final String MIME_BASE = "vnd.android.cursor.item/vnd.com.whatsapp";

    public static final class Person {
        public String name = "";
        public long cid = 0;
        public String pkg = "com.whatsapp";
        public String number = "";
        public boolean wa = false;
        public final Map<String, Long> ids = new HashMap<String, Long>();
        public final Map<String, String> mime = new HashMap<String, String>();
    }

    public static List<Person> load(Context ctx) {
        Map<Long, Person> people = new HashMap<Long, Person>();
        Cursor c = null;
        try {
            c = ctx.getContentResolver().query(ContactsContract.CommonDataKinds.Phone.CONTENT_URI,
                    new String[]{"contact_id", "display_name", "data1"}, null, null, null);
            while (c != null && c.moveToNext()) {
                long cid = c.getLong(0);
                String name = c.getString(1);
                if (name == null) {
                    continue;
                }
                Person p = people.get(cid);
                if (p == null) {
                    p = new Person();
                    p.name = name;
                    p.cid = cid;
                    people.put(cid, p);
                }
                String n = normalize(c.getString(2));
                if (p.number.length() == 0 && n.length() > 0) {
                    p.number = n;
                }
            }
        } finally {
            if (c != null) {
                c.close();
            }
        }
        c = null;
        try {
            c = ctx.getContentResolver().query(ContactsContract.Data.CONTENT_URI,
                    new String[]{"_id", "contact_id", "display_name", "mimetype"},
                    "mimetype LIKE ?", new String[]{MIME_BASE + "%"}, null);
            while (c != null && c.moveToNext()) {
                long did = c.getLong(0);
                long cid = c.getLong(1);
                String name = c.getString(2);
                String mime = c.getString(3);
                if (mime == null) {
                    continue;
                }
                boolean business = mime.contains(".w4b.");
                String kind = mime.substring(mime.lastIndexOf("whatsapp.") + 9).replace("w4b.", "");
                Person p = people.get(cid);
                if (p == null) {
                    p = new Person();
                    p.name = name == null ? "" : name;
                    p.cid = cid;
                    people.put(cid, p);
                }
                if (p.wa && p.pkg.equals("com.whatsapp") && business) {
                    continue;
                }
                if (business && !p.wa) {
                    p.pkg = "com.whatsapp.w4b";
                }
                p.wa = true;
                p.ids.put(kind, did);
                p.mime.put(kind, mime);
            }
        } finally {
            if (c != null) {
                c.close();
            }
        }
        List<Person> out = new ArrayList<Person>();
        for (Person p : people.values()) {
            if (p.name.length() > 0) {
                out.add(p);
            }
        }
        return out;
    }

    public static String normalize(String num) {
        String d = num == null ? "" : num.replaceAll("[^0-9]", "");
        if (d.length() == 10) {
            return "91" + d;
        }
        if (d.length() == 11 && d.startsWith("0")) {
            return "91" + d.substring(1);
        }
        return d;
    }

    public static String phoneFor(Context ctx, long cid) {
        Cursor c = null;
        try {
            c = ctx.getContentResolver().query(ContactsContract.CommonDataKinds.Phone.CONTENT_URI,
                    new String[]{"data1"}, "contact_id=?", new String[]{String.valueOf(cid)}, null);
            while (c != null && c.moveToNext()) {
                String n = normalize(c.getString(0));
                if (n.length() > 0) {
                    return n;
                }
            }
        } finally {
            if (c != null) {
                c.close();
            }
        }
        return "";
    }

    public static void call(Context ctx, Person p, boolean video) throws Exception {
        String key = video ? "video.call" : "voip.call";
        Long did = p.ids.get(key);
        if (did == null) {
            throw new Exception("is contact ke liye WhatsApp " + (video ? "video" : "voice") + " call nahi mila");
        }
        Intent i = new Intent(Intent.ACTION_VIEW);
        i.setDataAndType(Uri.parse("content://com.android.contacts/data/" + did), p.mime.get(key));
        i.setPackage(p.pkg);
        i.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
        ctx.startActivity(i);
    }

    public static void chat(Context ctx, Person p, String number, String text) throws Exception {
        Intent i = new Intent(Intent.ACTION_VIEW,
                Uri.parse("https://wa.me/" + number + "?text=" + URLEncoder.encode(text, "UTF-8")));
        i.setPackage(p.pkg);
        i.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
        ctx.getSharedPreferences("jarvis_prefs", 0).edit()
                .putLong("access_send_until", System.currentTimeMillis() + 25000).apply();
        ctx.startActivity(i);
    }

    public static boolean accessibilityOn(Context ctx) {
        try {
            String v = android.provider.Settings.Secure.getString(ctx.getContentResolver(),
                    "enabled_accessibility_services");
            return v != null && v.contains("JarvisAccessService");
        } catch (Exception e) {
            return false;
        }
    }
}
