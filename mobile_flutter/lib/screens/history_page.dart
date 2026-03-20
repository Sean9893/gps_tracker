import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:latlong2/latlong.dart';
import '../app_config.dart';
import '../models/models.dart';
import '../services/api_service.dart';

class HistoryPage extends StatefulWidget {
  final String deviceId;
  const HistoryPage({super.key, required this.deviceId});

  @override
  State<HistoryPage> createState() => _HistoryPageState();
}

class _HistoryPageState extends State<HistoryPage> {
  final api = ApiService();
  DateTime start = DateTime.now().toUtc().subtract(const Duration(hours: 1));
  DateTime end = DateTime.now().toUtc();
  List<GpsPoint> points = [];
  String? error;
  bool loading = false;

  Future<void> _pickStart() async {
    final d = await showDatePicker(
      context: context,
      firstDate: DateTime(2020),
      lastDate: DateTime.now().add(const Duration(days: 365)),
      initialDate: start.toLocal(),
    );
    if (d != null) {
      setState(() {
        start = DateTime.utc(d.year, d.month, d.day, 0, 0, 0);
      });
    }
  }

  Future<void> _pickEnd() async {
    final d = await showDatePicker(
      context: context,
      firstDate: DateTime(2020),
      lastDate: DateTime.now().add(const Duration(days: 365)),
      initialDate: end.toLocal(),
    );
    if (d != null) {
      setState(() {
        end = DateTime.utc(d.year, d.month, d.day, 23, 59, 59);
      });
    }
  }

  Future<void> _query() async {
    setState(() {
      loading = true;
      error = null;
    });
    try {
      final result = await api.fetchHistory(deviceId: widget.deviceId, startUtc: start, endUtc: end);
      setState(() => points = result);
    } catch (e) {
      setState(() => error = e.toString());
    } finally {
      setState(() => loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final latlngs = points.map((e) => LatLng(e.lat, e.lng)).toList();
    final center = latlngs.isNotEmpty ? latlngs.first : const LatLng(31.2304, 121.4737);

    return Scaffold(
      appBar: AppBar(title: Text('History ${widget.deviceId}')),
      body: Column(
        children: [
          Padding(
            padding: const EdgeInsets.all(8),
            child: Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                ElevatedButton(onPressed: _pickStart, child: Text('Start ${start.toIso8601String().substring(0, 10)}')),
                ElevatedButton(onPressed: _pickEnd, child: Text('End ${end.toIso8601String().substring(0, 10)}')),
                ElevatedButton(onPressed: loading ? null : _query, child: const Text('Query history')),
              ],
            ),
          ),
          if (error != null) Padding(padding: const EdgeInsets.all(8), child: Text('Request failed: $error')),
          if (!loading && points.isEmpty)
            const Padding(
              padding: EdgeInsets.all(8),
              child: Text('No data'),
            ),
          Expanded(
            child: FlutterMap(
              options: MapOptions(initialCenter: center, initialZoom: 13),
              children: [
                TileLayer(
                  urlTemplate: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
                  userAgentPackageName: AppConfig.androidApplicationId,
                ),
                if (latlngs.isNotEmpty)
                  PolylineLayer(
                    polylines: [
                      Polyline(points: latlngs, strokeWidth: 4, color: Colors.blue),
                    ],
                  ),
                if (latlngs.isNotEmpty)
                  MarkerLayer(
                    markers: [
                      Marker(
                        point: latlngs.first,
                        width: 36,
                        height: 36,
                        child: const Icon(Icons.play_arrow, color: Colors.green),
                      ),
                      Marker(
                        point: latlngs.last,
                        width: 36,
                        height: 36,
                        child: const Icon(Icons.flag, color: Colors.red),
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
