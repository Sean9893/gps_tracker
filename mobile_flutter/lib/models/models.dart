class DeviceSummary {
  final String deviceId;
  final String deviceName;
  final bool online;
  final String? lastOnlineTime;

  DeviceSummary({
    required this.deviceId,
    required this.deviceName,
    required this.online,
    required this.lastOnlineTime,
  });

  factory DeviceSummary.fromJson(Map<String, dynamic> json) {
    return DeviceSummary(
      deviceId: json['device_id'] ?? '',
      deviceName: json['device_name'] ?? '',
      online: json['online'] ?? false,
      lastOnlineTime: json['last_online_time'],
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

  GpsPoint({
    required this.deviceId,
    required this.utcTime,
    required this.lat,
    required this.lng,
    required this.speed,
    required this.course,
    required this.satellites,
    required this.fix,
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
    );
  }
}

class DeviceStatus {
  final String deviceId;
  final bool online;
  final String? lastOnlineTime;
  final int? lastFix;
  final Map<String, dynamic>? lastLocation;

  DeviceStatus({
    required this.deviceId,
    required this.online,
    required this.lastOnlineTime,
    required this.lastFix,
    required this.lastLocation,
  });

  factory DeviceStatus.fromJson(Map<String, dynamic> json) {
    return DeviceStatus(
      deviceId: json['device_id'] ?? '',
      online: json['online'] ?? false,
      lastOnlineTime: json['last_online_time'],
      lastFix: json['last_fix'],
      lastLocation: json['last_location'],
    );
  }
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
