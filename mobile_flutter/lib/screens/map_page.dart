import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:latlong2/latlong.dart';
import '../app_config.dart';
import '../models/models.dart';
import '../services/api_service.dart';

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
      setState(() {
        latest = point;
        error = null;
      });
      if (point != null) {
        mapController.move(LatLng(point.lat, point.lng), 15);
      }
    } catch (e) {
      setState(() => error = e.toString());
    }
  }

  @override
  Widget build(BuildContext context) {
    final center = latest == null ? const LatLng(31.2304, 121.4737) : LatLng(latest!.lat, latest!.lng);
    return Scaffold(
      appBar: AppBar(title: Text('Live map ${widget.deviceId}')),
      body: Column(
        children: [
          if (error != null)
            Padding(
              padding: const EdgeInsets.all(8),
              child: Text('Request failed: $error', style: const TextStyle(color: Colors.red)),
            ),
          Expanded(
            child: FlutterMap(
              mapController: mapController,
              options: MapOptions(initialCenter: center, initialZoom: 15),
              children: [
                TileLayer(
                  urlTemplate: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
                  userAgentPackageName: AppConfig.androidApplicationId,
                ),
                if (latest != null)
                  MarkerLayer(
                    markers: [
                      Marker(
                        point: LatLng(latest!.lat, latest!.lng),
                        width: 40,
                        height: 40,
                        child: const Icon(Icons.location_pin, size: 40, color: Colors.red),
                      ),
                    ],
                  ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
