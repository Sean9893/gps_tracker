import 'package:flutter_test/flutter_test.dart';
import 'package:gps_tracker_app/main.dart';

void main() {
  testWidgets('app renders device list page', (WidgetTester tester) async {
    await tester.pumpWidget(const GpsApp());

    expect(find.text('Devices'), findsOneWidget);
  });
}
