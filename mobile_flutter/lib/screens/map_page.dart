import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:latlong2/latlong.dart';

import '../app_config.dart';
import '../models/models.dart';
import '../services/api_service.dart';
import '../utils/coordinate_converter.dart';

class MapPage extends StatefulWidget {
  final String deviceId;

  const MapPage({super.key, required this.deviceId});

  @override
  State<MapPage> createState() => _MapPageState();
}

class _MapPageState extends State<MapPage> {
  final api = ApiService();
  final mapController = MapController();
  Timer? timer;
  GpsPoint? latest;
  String? error;
  bool following = true;

  @override
  void initState() {
    super.initState();
    _load();
    timer = Timer.periodic(const Duration(seconds: 5), (_) => _load());
  }

  @override
  void dispose() {
    timer?.cancel();
    super.dispose();
  }

  Future<void> _load() async {
    try {
      final point = await api.fetchLatest(widget.deviceId);
      if (!mounted) return;
      setState(() {
        latest = point;
        error = null;
      });
      if (point != null && following) {
        mapController.move(
          CoordinateConverter.wgs84ToGcj02(point.lat, point.lng),
          16,
        );
      }
    } catch (e) {
      if (mounted) setState(() => error = e.toString());
    }
  }

  void _locate() {
    if (latest == null) return;
    setState(() => following = true);
    mapController.move(
      CoordinateConverter.wgs84ToGcj02(latest!.lat, latest!.lng),
      16,
    );
  }

  @override
  Widget build(BuildContext context) {
    final point = latest == null
        ? const LatLng(31.2304, 121.4737)
        : CoordinateConverter.wgs84ToGcj02(latest!.lat, latest!.lng);

    return Scaffold(
      appBar: AppBar(
        title: const Text('实时位置'),
        actions: [
          IconButton(
            tooltip: '定位车辆',
            onPressed: latest == null ? null : _locate,
            icon: const Icon(Icons.my_location),
          ),
        ],
      ),
      body: Stack(
        children: [
          FlutterMap(
            mapController: mapController,
            options: MapOptions(
              initialCenter: point,
              initialZoom: 16,
              onPositionChanged: (_, hasGesture) {
                if (hasGesture && following) {
                  setState(() => following = false);
                }
              },
            ),
            children: [
              TileLayer(
                urlTemplate: AppConfig.mapTileUrlTemplate,
                subdomains: AppConfig.mapTileSubdomains,
                userAgentPackageName: AppConfig.androidApplicationId,
              ),
              if (latest != null)
                MarkerLayer(
                  markers: [
                    Marker(
                      point: point,
                      width: 54,
                      height: 54,
                      child: Container(
                        decoration: BoxDecoration(
                          color: Colors.white,
                          shape: BoxShape.circle,
                          boxShadow: [
                            BoxShadow(
                              color: Colors.black.withValues(alpha: 0.18),
                              blurRadius: 8,
                            ),
                          ],
                        ),
                        child: const Icon(
                          Icons.directions_car_filled,
                          size: 30,
                          color: Color(0xFFC43D3D),
                        ),
                      ),
                    ),
                  ],
                ),
            ],
          ),
          if (error != null)
            Positioned(
              top: 12,
              left: 16,
              right: 16,
              child: Material(
                color: const Color(0xFFFFE8E6),
                borderRadius: BorderRadius.circular(8),
                child: Padding(
                  padding: const EdgeInsets.all(12),
                  child: Text(
                    '位置刷新失败：$error',
                    style: const TextStyle(color: Color(0xFF9F2D2D)),
                  ),
                ),
              ),
            ),
          if (latest != null)
            Positioned(
              left: 16,
              right: 16,
              bottom: 16,
              child: SafeArea(
                top: false,
                child: Material(
                  color: Colors.white,
                  borderRadius: BorderRadius.circular(8),
                  elevation: 2,
                  child: Padding(
                    padding: const EdgeInsets.all(14),
                    child: Row(
                      children: [
                        Expanded(
                          child: _MapMetric(
                            label: '速度',
                            value: '${latest!.speed.toStringAsFixed(1)} km/h',
                          ),
                        ),
                        Expanded(
                          child: _MapMetric(
                            label: '卫星',
                            value: '${latest!.satellites} 颗',
                          ),
                        ),
                        Expanded(
                          child: _MapMetric(
                            label: '定位',
                            value: latest!.fix == 1 ? '有效' : '无效',
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              ),
            ),
        ],
      ),
    );
  }
}

class _MapMetric extends StatelessWidget {
  final String label;
  final String value;

  const _MapMetric({required this.label, required this.value});

  @override
  Widget build(BuildContext context) {
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        Text(
          value,
          style: const TextStyle(fontWeight: FontWeight.w700),
          textAlign: TextAlign.center,
        ),
        const SizedBox(height: 2),
        Text(
          label,
          style: const TextStyle(color: Colors.black54, fontSize: 12),
        ),
      ],
    );
  }
}
