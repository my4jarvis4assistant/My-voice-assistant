package org.myassistant.myvoiceassistant;

import android.content.Intent;
import android.service.quicksettings.Tile;
import android.service.quicksettings.TileService;

/** Quick Settings tile: ek tap me Jarvis ka hamesha-sunna On/Off. */
public class JarvisTileService extends TileService {
    @Override
    public void onStartListening() {
        try {
            Tile t = getQsTile();
            if (t != null) {
                boolean on = getSharedPreferences("jarvis_prefs", 0).getBoolean("wake_enabled", false);
                t.setState(on ? Tile.STATE_ACTIVE : Tile.STATE_INACTIVE);
                t.updateTile();
            }
        } catch (Exception ignored) {
        }
    }

    @Override
    public void onClick() {
        try {
            Intent i = new Intent(this, JarvisTriggerActivity.class);
            i.setAction(JarvisTriggerActivity.ACTION_TOGGLE_WAKE);   // tap = Jarvis ka sunna On/Off
            i.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
            startActivityAndCollapse(i);
        } catch (Exception ignored) {
        }
    }
}
