package org.myassistant.myvoiceassistant;

import android.content.Intent;
import android.service.quicksettings.Tile;
import android.service.quicksettings.TileService;

/** Notification panel (Quick Settings) me "Jarvis" tile: ek tap me Jarvis ka panel kisi bhi app ke upar. */
public class JarvisTileService extends TileService {
    @Override
    public void onStartListening() {
        try {
            Tile t = getQsTile();
            if (t != null) {
                t.setState(Tile.STATE_INACTIVE);
                t.updateTile();
            }
        } catch (Exception ignored) {
        }
    }

    @Override
    public void onClick() {
        try {
            Intent i = new Intent(this, JarvisTriggerActivity.class);
            i.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
            startActivityAndCollapse(i);
        } catch (Exception ignored) {
        }
    }
}
