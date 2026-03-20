class AppConfig {
  const AppConfig._();

  static const String appName = 'GPS Tracker';
  static const String androidApplicationId = 'com.example.gps_tracker_app';

  // Release builds should pass --dart-define=API_BASE_URL=http(s)://host:port.
  static const String defaultApiBaseUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: 'http://121.43.25.166:8000',
  );
}

