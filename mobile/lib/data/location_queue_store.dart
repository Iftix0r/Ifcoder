import 'dart:convert';

import 'package:shared_preferences/shared_preferences.dart';

import '../core/constants.dart';
import 'models/location_ping.dart';

/// Internet vaqtincha yo'q bo'lganda yuborilmay qolgan joylashuv nuqtalarini
/// qurilmada saqlab turadi — keyingi muvaffaqiyatli urinishda tartib bilan
/// qayta yuboriladi. Native LocationQueueStore bilan bir xil mantiq.
class LocationQueueStore {
  static const _key = 'location_ping_queue';

  Future<List<LocationPingRequest>> pending() async {
    final prefs = await SharedPreferences.getInstance();
    final raw = prefs.getString(_key);
    if (raw == null || raw.isEmpty) return [];
    try {
      final list = jsonDecode(raw) as List<dynamic>;
      return list
          .map((item) => LocationPingRequest.fromJson(item as Map<String, dynamic>))
          .toList();
    } catch (_) {
      return [];
    }
  }

  Future<void> replace(List<LocationPingRequest> items) async {
    final prefs = await SharedPreferences.getInstance();
    final trimmed = items.length > kLocationQueueMaxSize
        ? items.sublist(items.length - kLocationQueueMaxSize)
        : items;
    await prefs.setString(_key, jsonEncode(trimmed.map((e) => e.toJson()).toList()));
  }
}
