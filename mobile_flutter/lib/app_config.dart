class AppConfig {
  const AppConfig._();

  static const String appName = 'GPS Tracker';
  static const String androidApplicationId = 'com.example.gps_tracker_app';
  static const String mapTileUrlTemplate =
      'https://webrd0{s}.is.autonavi.com/appmaptile?'
      'lang=zh_cn&size=1&scale=1&style=8&x={x}&y={y}&z={z}';
  static const List<String> mapTileSubdomains = ['1', '2', '3', '4'];

  // Release builds should pass --dart-define=API_BASE_URL=http(s)://host:port.
  static const String defaultApiBaseUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: 'http://121.43.25.166:8000',
  );
}
