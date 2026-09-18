import 'package:permission_handler/permission_handler.dart';

/// Barcha runtime ruhsatlarni so'rash mantiqi shu yerda to'plangan — native
/// ilovadagi PermissionsHelper'ga mos ketma-ketlik: avval foreground joylashuv,
/// keyin (alohida qadam sifatida) background joylashuv, so'ng bildirishnoma,
/// SMS va batareyka optimizatsiyasidan chiqarish.
class PermissionsService {
  Future<bool> hasForegroundLocation() async {
    final status = await Permission.locationWhenInUse.status;
    return status.isGranted;
  }

  Future<bool> requestForegroundLocation() async {
    final status = await Permission.locationWhenInUse.request();
    return status.isGranted;
  }

  Future<bool> hasBackgroundLocation() async {
    final status = await Permission.locationAlways.status;
    return status.isGranted;
  }

  /// Android 10+ da bu alohida, ikkinchi qadam bo'lishi shart — fine/coarse
  /// bilan bir vaqtda so'ralsa, tizim buni rad etadi.
  Future<bool> requestBackgroundLocation() async {
    final status = await Permission.locationAlways.request();
    return status.isGranted;
  }

  Future<bool> hasNotifications() async {
    final status = await Permission.notification.status;
    return status.isGranted;
  }

  Future<bool> requestNotifications() async {
    final status = await Permission.notification.request();
    return status.isGranted;
  }

  Future<bool> hasSms() async {
    final status = await Permission.sms.status;
    return status.isGranted;
  }

  Future<bool> requestSms() async {
    final status = await Permission.sms.request();
    return status.isGranted;
  }

  /// Ko'p OEM qurilmalarida (Xiaomi/MIUI, Samsung va h.k.) foreground xizmat ham
  /// batareyka optimizatsiyasi tomonidan to'xtatib qo'yiladi — bu ruxsat/xizmat
  /// xatosi emas, faqat "Cheklanmagan" rejimi joylashuv doimiy kelishiga yordam beradi.
  Future<bool> isIgnoringBatteryOptimizations() async {
    final status = await Permission.ignoreBatteryOptimizations.status;
    return status.isGranted;
  }

  Future<bool> requestIgnoreBatteryOptimizations() async {
    final status = await Permission.ignoreBatteryOptimizations.request();
    return status.isGranted;
  }

  /// Login paytida ketma-ket so'raladigan to'liq ruxsatlar zanjiri.
  Future<void> requestFullChain() async {
    if (!await hasForegroundLocation()) {
      final granted = await requestForegroundLocation();
      if (!granted) return;
    }
    if (!await hasBackgroundLocation()) {
      await requestBackgroundLocation();
    }
    if (!await hasNotifications()) {
      await requestNotifications();
    }
    if (!await hasSms()) {
      await requestSms();
    }
    if (!await isIgnoringBatteryOptimizations()) {
      await requestIgnoreBatteryOptimizations();
    }
  }
}
