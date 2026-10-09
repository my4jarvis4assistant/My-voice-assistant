package org.myassistant.myvoiceassistant;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
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
        String message = intent.getStringExtra("jarvis_message");
        if (message == null || message.length() == 0) {
            message = "timer".equals(type) ? "Jarvis Timer complete" : "Jarvis Alarm";
        }
        showNotification(context, type, message);
    }

    private void showNotification(Context context, String type, String message) {
        NotificationManager manager = (NotificationManager)
                context.getSystemService(Context.NOTIFICATION_SERVICE);
        if (manager == null) return;

        Uri alarmSound = RingtoneManager.getDefaultUri(RingtoneManager.TYPE_ALARM);
        if (Build.VERSION.SDK_INT >= 26) {
            AudioAttributes audioAttributes = new AudioAttributes.Builder()
                    .setUsage(AudioAttributes.USAGE_ALARM)
                    .setContentType(AudioAttributes.CONTENT_TYPE_SONIFICATION)
                    .build();
            NotificationChannel channel = new NotificationChannel(
                    CHANNEL_ID, "JARVIS Alarm & Timer", NotificationManager.IMPORTANCE_HIGH);
            channel.setDescription("JARVIS alarms and timers");
            channel.enableVibration(true);
            channel.setSound(alarmSound, audioAttributes);
            manager.createNotificationChannel(channel);
        }

        Notification.Builder builder;
        if (Build.VERSION.SDK_INT >= 26) {
            builder = new Notification.Builder(context, CHANNEL_ID);
        } else {
            builder = new Notification.Builder(context)
                    .setSound(alarmSound)
                    .setPriority(Notification.PRIORITY_MAX);
        }
        builder.setSmallIcon(android.R.drawable.ic_lock_idle_alarm)
                .setContentTitle("timer".equals(type) ? "JARVIS Timer" : "JARVIS Alarm")
                .setContentText(message)
                .setCategory(Notification.CATEGORY_ALARM)
                .setAutoCancel(true)
                .setVibrate(new long[]{0, 500, 300, 500});

        manager.notify("timer".equals(type) ? 7002 : 7001, builder.build());
    }
}
