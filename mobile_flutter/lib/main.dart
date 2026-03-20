import 'package:flutter/material.dart';
import 'app_config.dart';
import 'screens/device_list_page.dart';

void main() {
  runApp(const GpsApp());
}

class GpsApp extends StatelessWidget {
  const GpsApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: AppConfig.appName,
      theme: ThemeData(
        colorSchemeSeed: Colors.blue,
        useMaterial3: true,
      ),
      home: const DeviceListPage(),
    );
  }
}
