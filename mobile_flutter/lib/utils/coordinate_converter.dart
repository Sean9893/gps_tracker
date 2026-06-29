import 'dart:math' as math;

import 'package:latlong2/latlong.dart';

class CoordinateConverter {
  const CoordinateConverter._();

  static const double _a = 6378245.0;
  static const double _ee = 0.00669342162296594323;

  static LatLng wgs84ToGcj02(double lat, double lng) {
    if (_outsideChina(lat, lng)) return LatLng(lat, lng);

    var dLat = _transformLat(lng - 105.0, lat - 35.0);
    var dLng = _transformLng(lng - 105.0, lat - 35.0);
    final radLat = lat / 180.0 * math.pi;
    var magic = math.sin(radLat);
    magic = 1 - _ee * magic * magic;
    final sqrtMagic = math.sqrt(magic);
    dLat = (dLat * 180.0) / ((_a * (1 - _ee)) / (magic * sqrtMagic) * math.pi);
    dLng = (dLng * 180.0) / (_a / sqrtMagic * math.cos(radLat) * math.pi);
    return LatLng(lat + dLat, lng + dLng);
  }

  static LatLng gcj02ToWgs84(double lat, double lng) {
    if (_outsideChina(lat, lng)) return LatLng(lat, lng);
    final converted = wgs84ToGcj02(lat, lng);
    return LatLng(lat * 2 - converted.latitude, lng * 2 - converted.longitude);
  }

  static bool _outsideChina(double lat, double lng) {
    return lng < 72.004 || lng > 137.8347 || lat < 0.8293 || lat > 55.8271;
  }

  static double _transformLat(double x, double y) {
    var result = -100.0 +
        2.0 * x +
        3.0 * y +
        0.2 * y * y +
        0.1 * x * y +
        0.2 * math.sqrt(x.abs());
    result += (20.0 * math.sin(6.0 * x * math.pi) +
            20.0 * math.sin(2.0 * x * math.pi)) *
        2.0 /
        3.0;
    result +=
        (20.0 * math.sin(y * math.pi) + 40.0 * math.sin(y / 3.0 * math.pi)) *
            2.0 /
            3.0;
    result += (160.0 * math.sin(y / 12.0 * math.pi) +
            320 * math.sin(y * math.pi / 30.0)) *
        2.0 /
        3.0;
    return result;
  }

  static double _transformLng(double x, double y) {
    var result = 300.0 +
        x +
        2.0 * y +
        0.1 * x * x +
        0.1 * x * y +
        0.1 * math.sqrt(x.abs());
    result += (20.0 * math.sin(6.0 * x * math.pi) +
            20.0 * math.sin(2.0 * x * math.pi)) *
        2.0 /
        3.0;
    result +=
        (20.0 * math.sin(x * math.pi) + 40.0 * math.sin(x / 3.0 * math.pi)) *
            2.0 /
            3.0;
    result += (150.0 * math.sin(x / 12.0 * math.pi) +
            300.0 * math.sin(x / 30.0 * math.pi)) *
        2.0 /
        3.0;
    return result;
  }
}
