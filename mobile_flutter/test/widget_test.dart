import 'package:flutter_test/flutter_test.dart';
import 'package:gps_tracker_app/main.dart';

void main() {
  testWidgets('应用显示中文设备列表页', (WidgetTester tester) async {
    await tester.pumpWidget(const GpsApp());

    expect(find.text('轮椅定位'), findsOneWidget);
  });
}
