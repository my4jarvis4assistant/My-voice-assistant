package org.myassistant.myvoiceassistant;

import android.app.Activity;
import android.content.Intent;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.provider.Settings;
import android.widget.Toast;

/**
 * Home screen button yahin khulta hai. Ye koi screen nahi dikhata: turant Jarvis ka
 * floating panel (JarvisOverlayService) shuru karke band ho jata hai, isliye
 * aap home screen par hi rehte hain.
 */
public class JarvisTriggerActivity extends Activity {
    public static final String ACTION_TOGGLE_WAKE = "org.myassistant.TOGGLE_WAKE";

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        try {
            if (Build.VERSION.SDK_INT >= 23 && !Settings.canDrawOverlays(this)) {
                Toast.makeText(this,
                        "Jarvis ko 'Display over other apps' allow kijiye, phir button dobara dabaiye",
                        Toast.LENGTH_LONG).show();
                Intent perm = new Intent(Settings.ACTION_MANAGE_OVERLAY_PERMISSION,
                        Uri.parse("package:" + getPackageName()));
                perm.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
                startActivity(perm);
            } else {
                Intent svc = new Intent(this, JarvisOverlayService.class);
                if (ACTION_TOGGLE_WAKE.equals(getIntent().getAction())) {
                    boolean on = getSharedPreferences("jarvis_prefs", 0).getBoolean("wake_enabled", false);
                    svc.setAction(on ? JarvisOverlayService.ACTION_WAKE_OFF : JarvisOverlayService.ACTION_WAKE_ON);
                    Toast.makeText(this, on ? "Jarvis sunna band" : "Jarvis ab hamesha sun raha hai",
                            Toast.LENGTH_SHORT).show();
                } else {
                    svc.setAction(JarvisOverlayService.ACTION_TALK);
                }
                if (Build.VERSION.SDK_INT >= 26) {
                    startForegroundService(svc);
                } else {
                    startService(svc);
                }
            }
        } catch (Exception e) {
            Toast.makeText(this, "Jarvis shuru nahi ho paya: " + e, Toast.LENGTH_LONG).show();
        }
        finish();
        overridePendingTransition(0, 0);
    }
}
