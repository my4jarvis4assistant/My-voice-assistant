package org.myassistant.myvoiceassistant;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.media.AudioAttributes;
import android.media.RingtoneManager;
import android.net.Uri;
import android.os.Build;

public class JarvisAlarmReceiver extends BroadcastReceiver {

    private static final String CHANNEL_ID = "jarvis_alarm_channel";

    @Override
    public void onReceive(Context context, Intent intent) {
        String type = intent.getStringExtra("jarvis_type");
        if (type == null) {
            type = "alarm";
        }

        String title = "JARVIS " +
                ("timer".equals(type) ? "Timer" : "Alarm");
        String message = "timer".equals(type)
                ? "Timer complete."
                : "Alarm time reached.";

        showNotification(context, title, message);
    }

    private void showNotification(
            Context context,
            String title,
            String message) {

        NotificationManager manager =
                (NotificationManager) context.getSystemService(
                        Context.NOTIFICATION_SERVICE);

        Uri sound = RingtoneManager.getDefaultUri(
                RingtoneManager.TYPE_ALARM);

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            AudioAttributes attributes = new AudioAttributes.Builder()
                    .setUsage(AudioAttributes.USAGE_ALARM)
                    .setContentType(AudioAttributes.CONTENT_TYPE_SONIFICATION)
                    .build();

            NotificationChannel channel = new NotificationChannel(
                    CHANNEL_ID,
                    "JARVIS Alarm and Timer",
                    NotificationManager.IMPORTANCE_HIGH);
            channel.setDescription("JARVIS alarm and timer alerts");
            channel.setSound(sound, attributes);
            channel.enableVibration(true);
            manager.createNotificationChannel(channel);
        }

        Intent launchIntent = context.getPackageManager()
                .getLaunchIntentForPackage(context.getPackageName());

        PendingIntent contentIntent = null;
        if (launchIntent != null) {
            int flags = PendingIntent.FLAG_UPDATE_CURRENT
                    | PendingIntent.FLAG_IMMUTABLE;
            contentIntent = PendingIntent.getActivity(
                    context,
                    9001,
                    launchIntent,
                    flags);
        }

        Notification.Builder builder;
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            builder = new Notification.Builder(context, CHANNEL_ID);
        } else {
            builder = new Notification.Builder(context)
                    .setSound(sound);
        }

        builder.setSmallIcon(android.R.drawable.ic_lock_idle_alarm)
                .setContentTitle(title)
                .setContentText(message)
                .setAutoCancel(true)
                .setCategory(Notification.CATEGORY_ALARM)
                .setPriority(Notification.PRIORITY_MAX)
                .setVibrate(new long[]{0, 700, 400, 700});

        if (contentIntent != null) {
            builder.setContentIntent(contentIntent);
        }

        manager.notify(
                "timer".equals(type) ? 9002 : 9001,
                builder.build());
    }
}
