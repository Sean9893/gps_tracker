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
