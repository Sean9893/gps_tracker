class DeviceSummary {
  final String deviceId;
  final String deviceName;
  final bool online;
  final String? lastOnlineTime;
  final bool fallDetected;

  DeviceSummary({
    required this.deviceId,
    required this.deviceName,
    required this.online,
    required this.lastOnlineTime,
    required this.fallDetected,
  });

  factory DeviceSummary.fromJson(Map<String, dynamic> json) {
    return DeviceSummary(
      deviceId: json['device_id'] ?? '',
      deviceName: json['device_name'] ?? '',
      online: json['online'] ?? false,
      lastOnlineTime: json['last_online_time'],
      fallDetected: json['fall_detected'] ?? false,
    );
  }
}

class GpsPoint {
  final String deviceId;
  final DateTime utcTime;
  final double lat;
  final double lng;
  final double speed;
  final double course;
  final int satellites;
  final int fix;
  final bool moving;
  final double movementDistanceM;
  final int battery;

  GpsPoint({
    required this.deviceId,
    required this.utcTime,
    required this.lat,
    required this.lng,
    required this.speed,
    required this.course,
    required this.satellites,
    required this.fix,
    required this.moving,
    required this.movementDistanceM,
    required this.battery,
  });

  factory GpsPoint.fromJson(Map<String, dynamic> json) {
    return GpsPoint(
      deviceId: json['device_id'] ?? '',
      utcTime: DateTime.parse(json['utc_time']),
      lat: (json['lat'] as num).toDouble(),
      lng: (json['lng'] as num).toDouble(),
      speed: (json['speed'] as num).toDouble(),
      course: (json['course'] as num).toDouble(),
      satellites: json['satellites'] ?? 0,
      fix: json['fix'] ?? 0,
      moving: json['moving'] ?? false,
      movementDistanceM: (json['movement_distance_m'] as num?)?.toDouble() ?? 0,
      battery: json['battery'] ?? 0,
    );
  }
}

class DeviceStatus {
  final String deviceId;
  final bool online;
  final String? lastOnlineTime;
  final int? lastFix;
  final Map<String, dynamic>? lastLocation;
  final bool fallDetected;

  DeviceStatus({
    required this.deviceId,
    required this.online,
    required this.lastOnlineTime,
    required this.lastFix,
    required this.lastLocation,
    required this.fallDetected,
  });

  factory DeviceStatus.fromJson(Map<String, dynamic> json) {
    return DeviceStatus(
      deviceId: json['device_id'] ?? '',
      online: json['online'] ?? false,
      lastOnlineTime: json['last_online_time'],
      lastFix: json['last_fix'],
      lastLocation: json['last_location'],
      fallDetected: json['fall_detected'] ?? false,
    );
  }
}

class HealthData {
  final String deviceId;
  final int heartRate;
  final int spo2;
  final DateTime uploadTime;

  HealthData({
    required this.deviceId,
    required this.heartRate,
    required this.spo2,
    required this.uploadTime,
  });

  factory HealthData.fromJson(Map<String, dynamic> json) {
    return HealthData(
      deviceId: json['device_id'] ?? '',
      heartRate: json['heart_rate'] as int,
      spo2: json['spo2'] as int,
      uploadTime: DateTime.parse(json['upload_time']),
    );
  }

  String get heartRateText {
    if (heartRate <= 0 || heartRate > 200) return '-';
    return '$heartRate 次/分';
  }

  String get spo2Text => spo2 <= 0 ? '-' : '$spo2%';
}

class GeofenceConfig {
  final String deviceId;
  final bool configured;
  final bool enabled;
  final double? centerLat;
  final double? centerLng;
  final double? radiusM;
  final bool? inside;
  final double? distanceM;
  final DateTime? lastCheckTime;

  GeofenceConfig({
    required this.deviceId,
    required this.configured,
    required this.enabled,
    required this.centerLat,
    required this.centerLng,
    required this.radiusM,
    required this.inside,
    required this.distanceM,
    required this.lastCheckTime,
  });

  factory GeofenceConfig.fromJson(Map<String, dynamic> json) {
    return GeofenceConfig(
      deviceId: json['device_id'] ?? '',
      configured: json['configured'] ?? false,
      enabled: json['enabled'] ?? false,
      centerLat: (json['center_lat'] as num?)?.toDouble(),
      centerLng: (json['center_lng'] as num?)?.toDouble(),
      radiusM: (json['radius_m'] as num?)?.toDouble(),
      inside: json['inside'],
      distanceM: (json['distance_m'] as num?)?.toDouble(),
      lastCheckTime: json['last_check_time'] == null
          ? null
          : DateTime.parse(json['last_check_time']),
    );
  }
}
