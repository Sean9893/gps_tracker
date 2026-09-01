class AppConfig {
  const AppConfig._();

  static const String appName = '轮椅定位';
  static const String androidApplicationId = 'com.example.gps_tracker_app';
  static const String mapTileUrlTemplate =
      'https://webrd0{s}.is.autonavi.com/appmaptile?'
      'lang=zh_cn&size=1&scale=1&style=8&x={x}&y={y}&z={z}';
  static const List<String> mapTileSubdomains = ['1', '2', '3', '4'];

  // TODO: 替换为真实的客服/紧急联系电话号码。
  static const String emergencyPhoneNumber = '400-000-0000';

  // Release builds should pass --dart-define=API_BASE_URL=http(s)://host:port.
  static const String defaultApiBaseUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: 'http://115.29.222.45:8000',
  );
}
