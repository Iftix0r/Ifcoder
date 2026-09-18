import 'dart:async';
import 'dart:ui';

import 'package:flutter_background_service/flutter_background_service.dart';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';
import 'package:geolocator/geolocator.dart';

import '../core/constants.dart';
import '../data/api_client.dart';
import '../data/location_queue_store.dart';
import '../data/models/location_ping.dart';
import '../data/token_store.dart';
import 'device_info_service.dart';

/// Operator ilova ochiq/fonda bo'lgan vaqtda joylashuvni davriy ravishda serverga
/// yuboradi. Internet vaqtincha yo'q bo'lsa, nuqta [LocationQueueStore] orqali
/// qurilmada saqlanadi va keyingi muvaffaqiyatli davriy urinishda tartib bilan
/// qayta yuboriladi. Native LocationTrackingService'ning to'g'ridan-to'g'ri
/// Flutter/Dart ekvivalenti — bitta doimiy foreground xizmat sifatida ishlaydi.
class LocationService {
  static final _service = FlutterBackgroundService();

  static Future<void> initialize() async {
    final notifications = FlutterLocalNotificationsPlugin();
    const channel = AndroidNotificationChannel(
      kNotificationChannelOps,
      'Fon xizmatlari',
      description: 'Ifcoder Operator ish vaqtida joylashuvni serverga yuboradi',
      importance: Importance.low,
    );
    await notifications
        .resolvePlatformSpecificImplementation<AndroidFlutterLocalNotificationsPlugin>()
        ?.createNotificationChannel(channel);

    await _service.configure(
      iosConfiguration: IosConfiguration(),
      androidConfiguration: AndroidConfiguration(
        onStart: _onStart,
        autoStart: false,
        autoStartOnBoot: true,
        isForegroundMode: true,
        notificationChannelId: kNotificationChannelOps,
        initialNotificationTitle: 'Joylashuv kuzatilmoqda',
        initialNotificationContent: 'Ifcoder Operator ish vaqtida joylashuvni serverga yuboradi',
        foregroundServiceTypes: [AndroidForegroundType.location],
      ),
    );
  }

  static Future<void> start() async {
    if (!await _service.isRunning()) {
      await _service.startService();
    }
  }

  static Future<void> stop() async {
    if (await _service.isRunning()) {
      _service.invoke('stopService');
    }
  }

  /// Fon izolyatida ishlaydigan kirish nuqtasi — top-level/static bo'lishi shart.
  @pragma('vm:entry-point')
  static Future<void> _onStart(ServiceInstance service) async {
    DartPluginRegistrant.ensureInitialized();

    // Login qilinmagan bo'lsa (masalan qurilma qayta yoqilgandan keyin autoStartOnBoot
    // orqali chaqirilgan bo'lsa-yu, hali hech kim tizimga kirmagan bo'lsa) — darhol to'xtaymiz.
    if (!await TokenStore.instance.isLoggedIn()) {
      service.stopSelf();
      return;
    }

    if (service is AndroidServiceInstance) {
      service.setAsForegroundService();
    }

    service.on('stopService').listen((event) {
      service.stopSelf();
    });

    final queueStore = LocationQueueStore();
    final deviceInfo = DeviceInfoService();

    Future<void> tick() async {
      if (!await TokenStore.instance.isLoggedIn()) {
        service.stopSelf();
        return;
      }
      final permission = await Geolocator.checkPermission();
      if (permission == LocationPermission.denied || permission == LocationPermission.deniedForever) {
        return;
      }
      if (!await Geolocator.isLocationServiceEnabled()) {
        return;
      }

      Position position;
      try {
        position = await Geolocator.getCurrentPosition(
          locationSettings: const LocationSettings(accuracy: LocationAccuracy.high),
        );
      } catch (_) {
        return;
      }

      final (batteryLevel, batteryCharging) = await deviceInfo.batteryStatus();
      final networkType = await deviceInfo.networkType();

      final ping = LocationPingRequest(
        latitude: position.latitude,
        longitude: position.longitude,
        accuracy: position.accuracy,
        recordedAt: position.timestamp.toUtc().toIso8601String(),
        batteryLevel: batteryLevel,
        batteryCharging: batteryCharging,
        networkType: networkType,
      );

      await _flushQueueThenSend(queueStore, ping);
    }

    // Darhol birinchi urinish, so'ng har kLocationUpdateIntervalSeconds'da.
    await tick();
    Timer.periodic(const Duration(seconds: kLocationUpdateIntervalSeconds), (_) => tick());
  }

  /// Avval navbatdagi eski nuqtalarni, keyin joriy nuqtani tartib bilan yuboradi.
  /// Birortasi muvaffaqiyatsiz tugasa (masalan internet yo'q), o'sha va undan
  /// keyingi barcha nuqtalar navbatda saqlab qo'yiladi — keyingi urinishda davom etadi.
  static Future<void> _flushQueueThenSend(
    LocationQueueStore queueStore,
    LocationPingRequest current,
  ) async {
    final all = [...await queueStore.pending(), current];
    final remaining = <LocationPingRequest>[];
    var networkDown = false;
    for (final item in all) {
      if (networkDown) {
        remaining.add(item);
        continue;
      }
      final ok = await _trySend(item);
      if (!ok) {
        networkDown = true;
        remaining.add(item);
      }
    }
    await queueStore.replace(remaining);
  }

  static Future<bool> _trySend(LocationPingRequest item) async {
    try {
      await ApiClient.instance.postLocation(item);
      return true;
    } catch (_) {
      return false;
    }
  }
}
