import 'package:flutter_secure_storage/flutter_secure_storage.dart';

/// Auth tokeni va login-oldi FCM tokenini saqlaydi. Native ilovadagi
/// TokenStore'ga mos — token doim shifrlangan (EncryptedSharedPreferences/Keychain)
/// holatda saqlanadi.
class TokenStore {
  TokenStore._();
  static final TokenStore instance = TokenStore._();

  final _storage = const FlutterSecureStorage(aOptions: AndroidOptions());

  static const _keyToken = 'auth_token';
  static const _keyPendingFcm = 'pending_fcm_token';

  Future<String?> getToken() => _storage.read(key: _keyToken);

  Future<void> saveToken(String token) => _storage.write(key: _keyToken, value: token);

  Future<bool> isLoggedIn() async => (await getToken()) != null;

  Future<void> clear() => _storage.delete(key: _keyToken);

  /// Login qilinmagan holda kelgan FCM tokenini vaqtincha saqlaydi —
  /// login muvaffaqiyatli bo'lgach serverga ro'yxatdan o'tkaziladi.
  Future<void> savePendingFcmToken(String token) => _storage.write(key: _keyPendingFcm, value: token);

  Future<String?> takePendingFcmToken() async {
    final value = await _storage.read(key: _keyPendingFcm);
    if (value != null) {
      await _storage.delete(key: _keyPendingFcm);
    }
    return value;
  }
}
