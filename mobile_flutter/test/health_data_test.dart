import 'package:flutter_test/flutter_test.dart';
import 'package:gps_tracker_app/models/models.dart';

void main() {
  test('health data parses and formats normal values', () {
    final health = HealthData.fromJson({
      'device_id': 'gps_001',
      'heart_rate': 200,
      'spo2': 98,
      'upload_time': '2026-07-16T08:00:00Z',
    });

    expect(health.deviceId, 'gps_001');
    expect(health.heartRateText, '200 次/分');
    expect(health.spo2Text, '98%');
  });

  test('heart rate over 200 displays dash', () {
    final health = HealthData.fromJson({
      'device_id': 'gps_001',
      'heart_rate': 201,
      'spo2': 98,
      'upload_time': '2026-07-16T08:00:00Z',
    });

    expect(health.heartRateText, '-');
  });

  test('negative sentinel displays dash', () {
    final health = HealthData.fromJson({
      'device_id': 'gps_001',
      'heart_rate': -999,
      'spo2': -999,
      'upload_time': '2026-07-16T08:00:00Z',
    });

    expect(health.heartRateText, '-');
    expect(health.spo2Text, '-');
  });
}
