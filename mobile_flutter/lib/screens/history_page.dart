import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:intl/intl.dart';
import 'package:latlong2/latlong.dart';

import '../app_config.dart';
import '../models/models.dart';
import '../services/api_service.dart';
import '../utils/coordinate_converter.dart';

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

  @override
  void initState() {
    super.initState();
    _query();
  }

  Future<void> _pickStart() async {
    final date = await showDatePicker(
      context: context,
      firstDate: DateTime(2020),
      lastDate: DateTime.now().add(const Duration(days: 365)),
      initialDate: start.toLocal(),
      helpText: '选择开始日期',
    );
    if (date != null) {
      setState(() {
        start = DateTime.utc(date.year, date.month, date.day);
      });
    }
  }

  Future<void> _pickEnd() async {
    final date = await showDatePicker(
      context: context,
      firstDate: DateTime(2020),
      lastDate: DateTime.now().add(const Duration(days: 365)),
      initialDate: end.toLocal(),
      helpText: '选择结束日期',
    );
    if (date != null) {
      setState(() {
        end = DateTime.utc(date.year, date.month, date.day, 23, 59, 59);
      });
    }
  }

  Future<void> _query() async {
    setState(() {
      loading = true;
      error = null;
    });
    try {
      final result = await api.fetchHistory(
        deviceId: widget.deviceId,
        startUtc: start,
        endUtc: end,
      );
      if (mounted) setState(() => points = result);
    } catch (e) {
      if (mounted) setState(() => error = e.toString());
    } finally {
      if (mounted) setState(() => loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final latLngs = points
        .map((point) => CoordinateConverter.wgs84ToGcj02(point.lat, point.lng))
        .toList();
    final center =
        latLngs.isNotEmpty ? latLngs.first : const LatLng(31.2304, 121.4737);
    final dateFormat = DateFormat('MM月dd日');

    return Scaffold(
      appBar: AppBar(title: const Text('历史轨迹')),
      body: Column(
        children: [
          Container(
            padding: const EdgeInsets.fromLTRB(16, 10, 16, 12),
            color: Theme.of(context).colorScheme.surface,
            child: Column(
              children: [
                Row(
                  children: [
                    Expanded(
                      child: OutlinedButton.icon(
                        onPressed: _pickStart,
                        icon: const Icon(Icons.calendar_today_outlined),
                        label: Text('开始 ${dateFormat.format(start.toLocal())}'),
                      ),
                    ),
                    const SizedBox(width: 10),
                    Expanded(
                      child: OutlinedButton.icon(
                        onPressed: _pickEnd,
                        icon: const Icon(Icons.event_outlined),
                        label: Text('结束 ${dateFormat.format(end.toLocal())}'),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 8),
                SizedBox(
                  width: double.infinity,
                  child: FilledButton.icon(
                    onPressed: loading ? null : _query,
                    icon: loading
                        ? const SizedBox(
                            width: 18,
                            height: 18,
                            child: CircularProgressIndicator(strokeWidth: 2),
                          )
                        : const Icon(Icons.search),
                    label: Text(loading ? '查询中' : '查询轨迹'),
                  ),
                ),
                if (error != null)
                  Padding(
                    padding: const EdgeInsets.only(top: 8),
                    child: Text(
                      '查询失败：$error',
                      style: const TextStyle(color: Color(0xFFC43D3D)),
                    ),
                  ),
              ],
            ),
          ),
          Expanded(
            child: Stack(
              children: [
                FlutterMap(
                  options: MapOptions(
                    initialCenter: center,
                    initialZoom: 13,
                  ),
                  children: [
                    TileLayer(
                      urlTemplate: AppConfig.mapTileUrlTemplate,
                      subdomains: AppConfig.mapTileSubdomains,
                      userAgentPackageName: AppConfig.androidApplicationId,
                    ),
                    if (latLngs.isNotEmpty)
                      PolylineLayer(
                        polylines: [
                          Polyline(
                            points: latLngs,
                            strokeWidth: 5,
                            color: const Color(0xFF176B5B),
                          ),
                        ],
                      ),
                    if (latLngs.isNotEmpty)
                      MarkerLayer(
                        markers: [
                          Marker(
                            point: latLngs.first,
                            width: 42,
                            height: 42,
                            child: const Icon(
                              Icons.play_circle_fill,
                              color: Color(0xFF18794E),
                              size: 34,
                            ),
                          ),
                          Marker(
                            point: latLngs.last,
                            width: 42,
                            height: 42,
                            child: const Icon(
                              Icons.flag_circle,
                              color: Color(0xFFC43D3D),
                              size: 34,
                            ),
                          ),
                        ],
                      ),
                  ],
                ),
                if (!loading && points.isEmpty)
                  const Center(
                    child: Material(
                      color: Colors.white,
                      borderRadius: BorderRadius.all(Radius.circular(8)),
                      child: Padding(
                        padding:
                            EdgeInsets.symmetric(horizontal: 20, vertical: 14),
                        child: Text('这个时间段没有轨迹数据'),
                      ),
                    ),
                  ),
                if (points.isNotEmpty)
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
                          padding: const EdgeInsets.all(12),
                          child: Text(
                            '共 ${points.length} 个定位点  ·  '
                            '${DateFormat('MM-dd HH:mm').format(points.first.utcTime.toLocal())}'
                            ' 至 '
                            '${DateFormat('MM-dd HH:mm').format(points.last.utcTime.toLocal())}',
                            textAlign: TextAlign.center,
                            style: const TextStyle(fontWeight: FontWeight.w600),
                          ),
                        ),
                      ),
                    ),
                  ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
