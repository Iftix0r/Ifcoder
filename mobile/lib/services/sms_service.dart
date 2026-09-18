import 'package:flutter/services.dart';

/// Mijozga SMS'ni to'g'ridan-to'g'ri telefonning o'z SmsManager'i orqali yuboradi —
/// uchinchi tomon SMS-gateway API'siz. Native ko'prik: MainActivity.kt.
class SmsService {
  static const _channel = MethodChannel('uz.ifcoder.operator/sms');

  Future<bool> sendSms(String phone, String text) async {
    if (phone.trim().isEmpty) return false;
    try {
      final result = await _channel.invokeMethod<bool>('sendSms', {
        'phone': phone,
        'message': text,
      });
      return result ?? false;
    } catch (_) {
      return false;
    }
  }
}
