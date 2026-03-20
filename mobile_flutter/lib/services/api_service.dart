import 'dart:convert';
import 'package:http/http.dart' as http;
import '../app_config.dart';
import '../models/models.dart';

class ApiService {
  // Android emulator should use 10.0.2.2; release builds should override with
  // --dart-define=API_BASE_URL=http(s)://your-server:8000
  static const String baseUrl = AppConfig.defaultApiBaseUrl;
  static const Duration _timeout = Duration(seconds: 6);

  Future<List<DeviceSummary>> fetchDevices() async {
    final uri = Uri.parse('$baseUrl/api/device/list');
    final resp = await http.get(uri).timeout(_timeout);
    final body = _decode(resp);
    final data = body['data'] as List<dynamic>? ?? [];
    return data.map((e) => DeviceSummary.fromJson(e)).toList();
  }

  Future<GpsPoint?> fetchLatest(String deviceId) async {
    final uri = Uri.parse('$baseUrl/api/gps/latest?device_id=$deviceId');
    final resp = await http.get(uri).timeout(_timeout);
    final body = _decode(resp);
    if (body['code'] != 0 || body['data'] == null) return null;
    return GpsPoint.fromJson(body['data']);
  }

  Future<DeviceStatus> fetchStatus(String deviceId) async {
    final uri = Uri.parse('$baseUrl/api/device/status?device_id=$deviceId');
    final resp = await http.get(uri).timeout(_timeout);
    final body = _decode(resp);
    if (body['code'] != 0 || body['data'] == null) {
      throw Exception(body['msg'] ?? 'fetch status failed');
    }
    return DeviceStatus.fromJson(body['data']);
  }

  Future<List<GpsPoint>> fetchHistory({
    required String deviceId,
    required DateTime startUtc,
    required DateTime endUtc,
  }) async {
    final uri = Uri.parse(
      '$baseUrl/api/gps/history?device_id=$deviceId'
      '&start=${Uri.encodeQueryComponent(startUtc.toIso8601String())}'
      '&end=${Uri.encodeQueryComponent(endUtc.toIso8601String())}',
    );
    final resp = await http.get(uri).timeout(_timeout);
    final body = _decode(resp);
    if (body['code'] != 0) {
      throw Exception(body['msg'] ?? 'fetch history failed');
    }
    final data = body['data'] as List<dynamic>? ?? [];
    return data.map((e) => GpsPoint.fromJson(e)).toList();
  }

  Map<String, dynamic> _decode(http.Response resp) {
    final obj = jsonDecode(resp.body) as Map<String, dynamic>;
    if (resp.statusCode != 200) {
      throw Exception(obj['msg'] ?? 'http ${resp.statusCode}');
    }
    return obj;
  }
}
