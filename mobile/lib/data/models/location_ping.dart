class LocationPingRequest {
  final double latitude;
  final double longitude;
  final double? accuracy;
  final String recordedAt;
  final int? batteryLevel;
  final bool? batteryCharging;
  final String? networkType;

  const LocationPingRequest({
    required this.latitude,
    required this.longitude,
    required this.accuracy,
    required this.recordedAt,
    this.batteryLevel,
    this.batteryCharging,
    this.networkType,
  });

  Map<String, dynamic> toJson() => {
        'latitude': latitude,
        'longitude': longitude,
        'accuracy': accuracy,
        'recorded_at': recordedAt,
        'battery_level': batteryLevel,
        'battery_charging': batteryCharging,
        'network_type': networkType,
      };

  factory LocationPingRequest.fromJson(Map<String, dynamic> json) => LocationPingRequest(
        latitude: (json['latitude'] as num).toDouble(),
        longitude: (json['longitude'] as num).toDouble(),
        accuracy: (json['accuracy'] as num?)?.toDouble(),
        recordedAt: json['recorded_at'] as String,
        batteryLevel: json['battery_level'] as int?,
        batteryCharging: json['battery_charging'] as bool?,
        networkType: json['network_type'] as String?,
      );
}
