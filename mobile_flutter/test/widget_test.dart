import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gps_tracker_app/main.dart';
import 'package:gps_tracker_app/models/models.dart';
import 'package:gps_tracker_app/screens/device_detail_page.dart';

void main() {
  testWidgets('应用显示中文设备列表页', (WidgetTester tester) async {
    await tester.pumpWidget(const GpsApp());

    expect(find.text('轮椅定位'), findsOneWidget);
  });

  testWidgets('health summary displays dash for unstable heart rate', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: HealthSummaryCard(
            health: HealthData(
              deviceId: 'gps_001',
              heartRate: 201,
              spo2: 98,
              uploadTime: DateTime.utc(2026, 7, 16, 8),
            ),
          ),
        ),
      ),
    );

    expect(find.text('心率'), findsOneWidget);
    expect(find.text('——'), findsOneWidget);
    expect(find.text('血氧'), findsOneWidget);
    expect(find.text('98%'), findsOneWidget);
  });

  testWidgets('health summary uses placeholders without data', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      const MaterialApp(
        home: Scaffold(body: HealthSummaryCard(health: null)),
      ),
    );

    expect(find.text('——'), findsNWidgets(2));
  });
}
