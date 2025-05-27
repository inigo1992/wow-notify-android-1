package com.example.wownotify

import android.app.*
import android.content.Intent
import android.content.pm.ServiceInfo
import android.media.AudioAttributes
import android.os.Build
import android.os.IBinder
import com.example.wownotify.R
import androidx.core.app.NotificationCompat
import java.net.DatagramPacket
import java.net.DatagramSocket
import java.net.InetSocketAddress
import kotlinx.coroutines.*

class ForegroundService : Service() {
    private val serviceScope = CoroutineScope(Dispatchers.IO + Job())
    private var socket: DatagramSocket? = null
    
    override fun onCreate() {
        super.onCreate()
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            startForeground(NOTIFICATION_ID, createNotification(), ServiceInfo.FOREGROUND_SERVICE_TYPE_DATA_SYNC)
        } else {
            startForeground(NOTIFICATION_ID, createNotification())
        }
        startUdpListener()
    }
    
    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        return START_STICKY
    }
    
    override fun onBind(intent: Intent?): IBinder? = null
    
    private fun createNotification(): Notification {
        val channelId = "wow_notify_service"
        val channelName = "WoW Notify Service"
        
        val channel = NotificationChannel(
            channelId,
            channelName,
            NotificationManager.IMPORTANCE_LOW
        )
        
        val notificationManager = getSystemService(NotificationManager::class.java)
        notificationManager.createNotificationChannel(channel)
        
        return NotificationCompat.Builder(this, channelId)
            .setContentTitle("WoW Queue Monitor")
            .setContentText("Waiting for queue pop...")
            .setSmallIcon(android.R.drawable.ic_dialog_info)
            .setPriority(NotificationCompat.PRIORITY_LOW)
            .build()
    }
    
    private fun startUdpListener() {
        serviceScope.launch {
            try {
                android.util.Log.i("WoWNotify", "Starting UDP listener on port 9876")
                socket = DatagramSocket(null)
                socket?.reuseAddress = true
                socket?.bind(InetSocketAddress("0.0.0.0", 9876))
                
                android.util.Log.i("WoWNotify", "UDP socket bound successfully")
                val buffer = ByteArray(1024)
                val packet = DatagramPacket(buffer, buffer.size)
                
                while (true) {
                    android.util.Log.d("WoWNotify", "Waiting for UDP packet...")
                    socket?.receive(packet)
                    val message = String(packet.data, 0, packet.length)
                    android.util.Log.i("WoWNotify", "Received UDP packet: '$message' from ${packet.address}:${packet.port}")
                    
                    if (message.contains("queue_pop")) {
                        android.util.Log.i("WoWNotify", "Queue pop detected, showing notification")
                        showQueuePopNotification()
                    }
                }
            } catch (e: Exception) {
                android.util.Log.e("WoWNotify", "Error in UDP listener: ${e.message}")
                e.printStackTrace()
            }
        }
    }
    
    private fun showQueuePopNotification() {
        try {
            android.util.Log.i("WoWNotify", "Creating queue pop notification")
            val channelId = "wow_queue_pop"
            val channelName = "WoW Queue Pop"
            
            val soundUri = android.net.Uri.parse("android.resource://${packageName}/" + R.raw.pvpthroughqueue)
            val audioAttributes = AudioAttributes.Builder()
                .setContentType(AudioAttributes.CONTENT_TYPE_SONIFICATION)
                .setUsage(AudioAttributes.USAGE_NOTIFICATION)
                .build()

            val channel = NotificationChannel(
                channelId,
                channelName,
                NotificationManager.IMPORTANCE_HIGH
            ).apply {
                enableVibration(true)
                vibrationPattern = longArrayOf(0, 500, 200, 500)
                setSound(soundUri, audioAttributes)
            }
            
            val notificationManager = getSystemService(NotificationManager::class.java)
            notificationManager.createNotificationChannel(channel)
            android.util.Log.i("WoWNotify", "Created notification channel")
            
            val notification = NotificationCompat.Builder(this, channelId)
                .setContentTitle("Queue Pop!")
                .setContentText("Your queue has popped!")
                .setSmallIcon(android.R.drawable.ic_dialog_alert)
                .setPriority(NotificationCompat.PRIORITY_MAX)
                .setCategory(NotificationCompat.CATEGORY_ALARM)
                .setAutoCancel(true)
                .setVisibility(NotificationCompat.VISIBILITY_PUBLIC)
                .build()
            
            android.util.Log.i("WoWNotify", "Built notification, sending...")
            notificationManager.notify(QUEUE_POP_NOTIFICATION_ID, notification)
            android.util.Log.i("WoWNotify", "Notification sent successfully")
        } catch (e: Exception) {
            android.util.Log.e("WoWNotify", "Error showing notification: ${e.message}")
            e.printStackTrace()
        }
    }
    
    override fun onDestroy() {
        super.onDestroy()
        socket?.close()
        serviceScope.cancel()
    }
    
    companion object {
        private const val NOTIFICATION_ID = 1
        private const val QUEUE_POP_NOTIFICATION_ID = 2
    }
}
