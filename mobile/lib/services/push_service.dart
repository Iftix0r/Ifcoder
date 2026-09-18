import 'package:firebase_core/firebase_core.dart';
import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:flutter/widgets.dart';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';

import '../core/constants.dart';
import '../data/api_client.dart';
import '../data/token_store.dart';
import 'device_info_service.dart';
import 'sms_service.dart';

final FlutterLocalNotificationsPlugin _notifications = FlutterLocalNotificationsPlugin();

/// FCM data xabarlarini fon (app o'chirilgan/yopilgan) holatda ham qayta ishlash
/// uchun top-level kirish nuqtasi — Firebase talabi.
@pragma('vm:entry-point')
Future<void> firebaseMessagingBackgroundHandler(RemoteMessage message) async {
  WidgetsFlutterBinding.ensureInitialized();
  await Firebase.initializeApp();
  await _initNotificationChannels();
  await PushService.handleMessage(message);
}

Future<void> _initNotificationChannels() async {
  const androidInit = AndroidInitializationSettings('@mipmap/ic_launcher');
  await _notifications.initialize(settings: const InitializationSettings(android: androidInit));

  const opsChannel = AndroidNotificationChannel(
    kNotificationChannelOps,
    'Fon xizmatlari',
    description: 'Ifcoder Operator ish vaqtida joylashuvni serverga yuboradi',
    importance: Importance.low,
  );
  const tasksChannel = AndroidNotificationChannel(
    kNotificationChannelTasks,
    'Vazifa bildirishnomalari',
    description: 'Yangi yoki yangilangan vazifalar haqida bildirishnoma',
    importance: Importance.high,
  );
  final androidPlugin =
      _notifications.resolvePlatformSpecificImplementation<AndroidFlutterLocalNotificationsPlugin>();
  await androidPlugin?.createNotificationChannel(opsChannel);
  await androidPlugin?.createNotificationChannel(tasksChannel);
}

/// Push-bildirishnoma va data-xabarlarni boshqaradi. Native FcmService bilan
/// bir xil ikkita xabar turini qo'llab-quvvatlaydi:
/// - "client_status_sms": serverdan kelgan matnni mijozga avtomatik SMS qilib yuboradi.
/// - "task_updated": vazifa yangilanganini bildiradi, bosilganda vazifalar ro'yxati ochiladi.
class PushService {
  static final ValueNotifier<bool> openTaskListRequested = ValueNotifier(false);

  static Future<void> initialize() async {
    await _initNotificationChannels();
    FirebaseMessaging.onBackgroundMessage(firebaseMessagingBackgroundHandler);
    FirebaseMessaging.onMessage.listen(handleMessage);
    FirebaseMessaging.onMessageOpenedApp.listen((_) => openTaskListRequested.value = true);

    FirebaseMessaging.instance.onTokenRefresh.listen((token) => _registerToken(token));

    final initialMessage = await FirebaseMessaging.instance.getInitialMessage();
    if (initialMessage != null) {
      openTaskListRequested.value = true;
    }
  }

  /// Login muvaffaqiyatli bo'lgandan so'ng chaqiriladi — hozirgi FCM tokenini oladi
  /// va serverga ro'yxatdan o'tkazadi (login-oldi kelgan token bo'lsa, o'shani ishlatadi).
  static Future<void> registerCurrentToken() async {
    final pending = await TokenStore.instance.takePendingFcmToken();
    final token = pending ?? await FirebaseMessaging.instance.getToken();
    if (token == null || token.isEmpty) return;
    await _registerToken(token);
  }

  static Future<void> _registerToken(String token) async {
    if (!await TokenStore.instance.isLoggedIn()) {
      await TokenStore.instance.savePendingFcmToken(token);
      return;
    }
    try {
      final deviceInfo = DeviceInfoService();
      await ApiClient.instance.registerDeviceToken(
        fcmToken: token,
        deviceId: await deviceInfo.model(),
        brand: await deviceInfo.brand(),
        osVersion: await deviceInfo.osVersion(),
        sdkInt: await deviceInfo.sdkInt(),
        appVersion: await deviceInfo.appVersion(),
      );
    } catch (_) {
      // Keyingi ochilishda qayta urinib ko'riladi.
    }
  }

  static Future<void> handleMessage(RemoteMessage message) async {
    switch (message.data['type']) {
      case 'client_status_sms':
        await _handleClientStatusSms(message);
        break;
      case 'task_updated':
        await _handleTaskUpdated(message);
        break;
    }
  }

  static Future<void> _handleClientStatusSms(RemoteMessage message) async {
    final phone = message.data['client_phone'] ?? '';
    final text = message.data['sms_text'] ?? '';
    final sent = await SmsService().sendSms(phone, text);
    await _showNotification(
      channelId: kNotificationChannelOps,
      title: sent ? 'SMS yuborildi' : 'SMS yuborilmadi',
      body: phone,
    );
  }

  static Future<void> _handleTaskUpdated(RemoteMessage message) async {
    final title = message.notification?.title ?? 'Vazifalarim';
    final body = message.notification?.body ?? '';
    await _showNotification(channelId: kNotificationChannelTasks, title: title, body: body);
  }

  static Future<void> _showNotification({
    required String channelId,
    required String title,
    required String body,
  }) async {
    final details = AndroidNotificationDetails(
      channelId,
      channelId == kNotificationChannelTasks ? 'Vazifa bildirishnomalari' : 'Fon xizmatlari',
      importance: Importance.high,
      priority: Priority.high,
    );
    await _notifications.show(
      id: DateTime.now().millisecondsSinceEpoch ~/ 1000,
      title: title,
      body: body,
      notificationDetails: NotificationDetails(android: details),
    );
  }
}
