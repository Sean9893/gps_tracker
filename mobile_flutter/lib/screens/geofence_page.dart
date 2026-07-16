import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:latlong2/latlong.dart';

import '../app_config.dart';
import '../models/models.dart';
import '../services/api_service.dart';
import '../utils/coordinate_converter.dart';
import '../widgets/wheelchair_icon.dart';

class GeofencePage extends StatefulWidget {
  final String deviceId;

  const GeofencePage({super.key, required this.deviceId});

  @override
  State<GeofencePage> createState() => _GeofencePageState();
}

class _GeofencePageState extends State<GeofencePage> {
  final api = ApiService();
  final mapController = MapController();

  bool loading = true;
  bool saving = false;
  bool enabled = true;
  String? error;
  GpsPoint? latest;
  GeofenceConfig? fence;
  double? centerLat;
  double? centerLng;
  double radiusM = 500;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() {
      loading = true;
      error = null;
    });
    try {
      final results = await Future.wait([
        api.fetchLatest(widget.deviceId),
        api.fetchGeofence(widget.deviceId),
      ]);
      final loadedLatest = results[0] as GpsPoint?;
      final loadedFence = results[1] as GeofenceConfig;
      setState(() {
        latest = loadedLatest;
        fence = loadedFence;
        enabled = loadedFence.configured ? loadedFence.enabled : true;
        radiusM = loadedFence.radiusM ?? 500;
        centerLat = loadedFence.centerLat ?? loadedLatest?.lat;
        centerLng = loadedFence.centerLng ?? loadedLatest?.lng;
      });
    } catch (e) {
      setState(() => error = e.toString());
    } finally {
      if (mounted) setState(() => loading = false);
    }
  }

  void _useLatestLocation() {
    if (latest == null) return;
    setState(() {
      centerLat = latest!.lat;
      centerLng = latest!.lng;
    });
    final displayPoint =
        CoordinateConverter.wgs84ToGcj02(latest!.lat, latest!.lng);
    mapController.move(displayPoint, 16);
  }

  void _onMapTap(LatLng displayPoint) {
    final rawPoint = CoordinateConverter.gcj02ToWgs84(
      displayPoint.latitude,
      displayPoint.longitude,
    );
    setState(() {
      centerLat = rawPoint.latitude;
      centerLng = rawPoint.longitude;
    });
  }

  Future<void> _save() async {
    if (centerLat == null || centerLng == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('请先选择围栏中心')),
      );
      return;
    }

    setState(() => saving = true);
    try {
      final saved = await api.saveGeofence(
        deviceId: widget.deviceId,
        centerLat: centerLat!,
        centerLng: centerLng!,
        radiusM: radiusM,
        enabled: enabled,
      );
      if (!mounted) return;
      setState(() => fence = saved);
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('电子围栏已保存')),
      );
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('保存失败：$e')),
      );
    } finally {
      if (mounted) setState(() => saving = false);
    }
  }

  String _statusText() {
    if (!(fence?.configured ?? false)) return '尚未设置';
    if (!(fence?.enabled ?? false)) return '已停用';
    if (fence?.inside == true) return '轮椅在围栏内';
    if (fence?.inside == false) return '轮椅已离开围栏';
    return '等待定位数据';
  }

  Color _statusColor() {
    if (!(fence?.enabled ?? false)) return Colors.grey;
    if (fence?.inside == true) return const Color(0xFF18794E);
    if (fence?.inside == false) return const Color(0xFFC43D3D);
    return const Color(0xFF8A5A00);
  }

  @override
  Widget build(BuildContext context) {
    final fallback = latest == null
        ? const LatLng(31.2304, 121.4737)
        : CoordinateConverter.wgs84ToGcj02(latest!.lat, latest!.lng);
    final fenceCenter = centerLat == null || centerLng == null
        ? null
        : CoordinateConverter.wgs84ToGcj02(centerLat!, centerLng!);
    final latestPoint = latest == null
        ? null
        : CoordinateConverter.wgs84ToGcj02(latest!.lat, latest!.lng);

    return Scaffold(
      appBar: AppBar(
        title: const Text('电子围栏'),
        actions: [
          IconButton(
            tooltip: '刷新',
            onPressed: _load,
            icon: const Icon(Icons.refresh),
          ),
        ],
      ),
      body: loading
          ? const Center(child: CircularProgressIndicator())
          : error != null
              ? _ErrorView(message: error!, onRetry: _load)
              : Column(
                  children: [
                    Container(
                      width: double.infinity,
                      padding: const EdgeInsets.fromLTRB(16, 12, 16, 14),
                      color: _statusColor().withValues(alpha: 0.10),
                      child: Row(
                        children: [
                          Icon(
                            fence?.inside == false
                                ? Icons.warning_amber_rounded
                                : Icons.shield_outlined,
                            color: _statusColor(),
                          ),
                          const SizedBox(width: 10),
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(
                                  _statusText(),
                                  style: TextStyle(
                                    fontSize: 17,
                                    fontWeight: FontWeight.w700,
                                    color: _statusColor(),
                                  ),
                                ),
                                if (fence?.distanceM != null)
                                  Text(
                                    '距围栏中心 ${fence!.distanceM!.toStringAsFixed(0)} 米',
                                  ),
                              ],
                            ),
                          ),
                          Switch(
                            value: enabled,
                            onChanged: (value) =>
                                setState(() => enabled = value),
                          ),
                        ],
                      ),
                    ),
                    Expanded(
                      child: FlutterMap(
                        mapController: mapController,
                        options: MapOptions(
                          initialCenter: fenceCenter ?? fallback,
                          initialZoom: 15,
                          onTap: (_, point) => _onMapTap(point),
                        ),
                        children: [
                          TileLayer(
                            urlTemplate: AppConfig.mapTileUrlTemplate,
                            subdomains: AppConfig.mapTileSubdomains,
                            userAgentPackageName:
                                AppConfig.androidApplicationId,
                          ),
                          if (fenceCenter != null)
                            CircleLayer(
                              circles: [
                                CircleMarker(
                                  point: fenceCenter,
                                  radius: radiusM,
                                  useRadiusInMeter: true,
                                  color: const Color(0xFF176B5B)
                                      .withValues(alpha: 0.18),
                                  borderColor: const Color(0xFF176B5B),
                                  borderStrokeWidth: 2,
                                ),
                              ],
                            ),
                          MarkerLayer(
                            markers: [
                              if (fenceCenter != null)
                                Marker(
                                  point: fenceCenter,
                                  width: 42,
                                  height: 42,
                                  child: const Icon(
                                    Icons.shield,
                                    color: Color(0xFF176B5B),
                                    size: 34,
                                  ),
                                ),
                              if (latestPoint != null)
                                Marker(
                                  point: latestPoint,
                                  width: 44,
                                  height: 44,
                                  child: const WheelchairIcon(
                                    size: 42,
                                    padding: 2,
                                  ),
                                ),
                            ],
                          ),
                        ],
                      ),
                    ),
                    SafeArea(
                      top: false,
                      child: Container(
                        padding: const EdgeInsets.fromLTRB(16, 12, 16, 14),
                        color: Theme.of(context).colorScheme.surface,
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Row(
                              children: [
                                const Text(
                                  '围栏半径',
                                  style: TextStyle(fontWeight: FontWeight.w700),
                                ),
                                const Spacer(),
                                Text('${radiusM.toStringAsFixed(0)} 米'),
                              ],
                            ),
                            Slider(
                              value: radiusM.clamp(50, 5000),
                              min: 50,
                              max: 5000,
                              divisions: 99,
                              label: '${radiusM.toStringAsFixed(0)} 米',
                              onChanged: (value) =>
                                  setState(() => radiusM = value),
                            ),
                            Row(
                              children: [
                                OutlinedButton.icon(
                                  onPressed: latest == null
                                      ? null
                                      : _useLatestLocation,
                                  icon: const Icon(Icons.my_location),
                                  label: const Text('使用轮椅位置'),
                                ),
                                const SizedBox(width: 12),
                                Expanded(
                                  child: FilledButton.icon(
                                    onPressed: saving ? null : _save,
                                    icon: saving
                                        ? const SizedBox(
                                            width: 18,
                                            height: 18,
                                            child: CircularProgressIndicator(
                                              strokeWidth: 2,
                                            ),
                                          )
                                        : const Icon(Icons.save_outlined),
                                    label: Text(saving ? '保存中' : '保存围栏'),
                                  ),
                                ),
                              ],
                            ),
                            const SizedBox(height: 6),
                            const Text(
                              '点击地图可调整中心，轮椅图标表示最新位置。',
                              style: TextStyle(
                                  fontSize: 12, color: Colors.black54),
                            ),
                          ],
                        ),
                      ),
                    ),
                  ],
                ),
    );
  }
}

class _ErrorView extends StatelessWidget {
  final String message;
  final VoidCallback onRetry;

  const _ErrorView({required this.message, required this.onRetry});

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.cloud_off, size: 48, color: Colors.grey),
            const SizedBox(height: 12),
            Text('加载失败：$message', textAlign: TextAlign.center),
            const SizedBox(height: 16),
            FilledButton.icon(
              onPressed: onRetry,
              icon: const Icon(Icons.refresh),
              label: const Text('重新加载'),
            ),
          ],
        ),
      ),
    );
  }
}
