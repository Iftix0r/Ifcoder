import 'package:dio/dio.dart';

import '../core/constants.dart';
import 'models/location_ping.dart';
import 'models/task.dart';
import 'token_store.dart';

/// Butun ilova uchun bitta Dio nusxasi — har bir so'rovga saqlangan token
/// avtomatik `Authorization: Token ...` header sifatida qo'shiladi.
class ApiClient {
  ApiClient._();
  static final ApiClient instance = ApiClient._();

  late final Dio _dio = Dio(
    BaseOptions(
      baseUrl: kBaseUrl,
      connectTimeout: const Duration(seconds: 15),
      receiveTimeout: const Duration(seconds: 15),
    ),
  )..interceptors.add(
      InterceptorsWrapper(
        onRequest: (options, handler) async {
          final token = await TokenStore.instance.getToken();
          if (token != null) {
            options.headers['Authorization'] = 'Token $token';
          }
          handler.next(options);
        },
      ),
    );

  Future<String> login(String username, String password) async {
    final response = await _dio.post('login/', data: {
      'username': username,
      'password': password,
    });
    return response.data['token'] as String;
  }

  Future<List<TaskDto>> getTasks() async {
    final response = await _dio.get('tasks/');
    return (response.data as List<dynamic>)
        .map((json) => TaskDto.fromJson(json as Map<String, dynamic>))
        .toList();
  }

  Future<bool> updateTaskStatus(int taskId, String status) async {
    final response = await _dio.post('tasks/$taskId/status/', data: {'status': status});
    return response.data['ok'] == true;
  }

  /// Muvaffaqiyatsiz bo'lsa exception tashlaydi — chaqiruvchi (LocationService)
  /// buni tarmoq xatosi deb hisoblab, nuqtani navbatga qo'shadi.
  Future<void> postLocation(LocationPingRequest ping) async {
    await _dio.post('location/', data: ping.toJson());
  }

  Future<void> registerDeviceToken({
    required String fcmToken,
    required String deviceId,
    String? brand,
    String? osVersion,
    int? sdkInt,
    String? appVersion,
  }) async {
    await _dio.post('device-token/', data: {
      'fcm_token': fcmToken,
      'device_id': deviceId,
      'brand': brand,
      'os_version': osVersion,
      'sdk_int': sdkInt,
      'app_version': appVersion,
    });
  }
}
