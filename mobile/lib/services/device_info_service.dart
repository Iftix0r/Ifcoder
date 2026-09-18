import 'package:battery_plus/battery_plus.dart';
import 'package:connectivity_plus/connectivity_plus.dart';
import 'package:device_info_plus/device_info_plus.dart';
import 'package:package_info_plus/package_info_plus.dart';

/// Serverga har safar (login/qurilma ro'yxatdan o'tkazish, joylashuv pingi)
/// yuboriladigan qurilma, batareyka va tarmoq ma'lumotlarini yig'uvchi
/// yordamchi klass. Har bir metod xatolikda null/"unknown" qaytaradi —
/// bitta ma'lumot manbai ishlamasa ham ping yuborishni to'xtatmaslik uchun.
class DeviceInfoService {
  Future<String> brand() async {
    try {
      final info = await DeviceInfoPlugin().androidInfo;
      return info.brand;
    } catch (_) {
      return '';
    }
  }

  Future<String> model() async {
    try {
      final info = await DeviceInfoPlugin().androidInfo;
      return info.model;
    } catch (_) {
      return '';
    }
  }

  Future<String> osVersion() async {
    try {
      final info = await DeviceInfoPlugin().androidInfo;
      return info.version.release;
    } catch (_) {
      return '';
    }
  }

  Future<int?> sdkInt() async {
    try {
      final info = await DeviceInfoPlugin().androidInfo;
      return info.version.sdkInt;
    } catch (_) {
      return null;
    }
  }

  Future<String> appVersion() async {
    try {
      final info = await PackageInfo.fromPlatform();
      return '${info.version} (${info.buildNumber})';
    } catch (_) {
      return '';
    }
  }

  /// @return (foiz 0-100 yoki null, zaryadlanyaptimi yoki null).
  Future<(int?, bool?)> batteryStatus() async {
    try {
      final battery = Battery();
      final level = await battery.batteryLevel;
      final state = await battery.batteryState;
      final charging = state == BatteryState.charging || state == BatteryState.full;
      return (level, charging);
    } catch (_) {
      return (null, null);
    }
  }

  /// @return "wifi", "mobile", "ethernet", "none" yoki "unknown".
  Future<String> networkType() async {
    try {
      final results = await Connectivity().checkConnectivity();
      if (results.contains(ConnectivityResult.wifi)) return 'wifi';
      if (results.contains(ConnectivityResult.mobile)) return 'mobile';
      if (results.contains(ConnectivityResult.ethernet)) return 'ethernet';
      if (results.contains(ConnectivityResult.none) || results.isEmpty) return 'none';
      return 'unknown';
    } catch (_) {
      return 'unknown';
    }
  }
}
