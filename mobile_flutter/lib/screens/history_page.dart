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
  final mapController = MapController();
  DateTime start = DateTime.now().toUtc().subtract(const Duration(hours: 1));
  DateTime end = DateTime.now().toUtc();
  List<GpsPoint> points = [];
  int selectedIndex = 0;
  String? error;
  bool loading = false;

  @override
  void initState() {
    super.initState();
    _query();
  }

  Future<int?> _pickSecond(int initialSecond) {
    var selected = initialSecond.toDouble();
    return showDialog<int>(
      context: context,
      builder: (context) => StatefulBuilder(
        builder: (context, setDialogState) => AlertDialog(
          title: const Text('选择秒数'),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(
                '${selected.round().toString().padLeft(2, '0')} 秒',
                style: const TextStyle(
                  fontSize: 24,
                  fontWeight: FontWeight.w700,
                ),
              ),
              Slider(
                value: selected,
                min: 0,
                max: 59,
                divisions: 59,
                label: selected.round().toString(),
                onChanged: (value) => setDialogState(() => selected = value),
              ),
            ],
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(context),
              child: const Text('取消'),
            ),
            FilledButton(
              onPressed: () => Navigator.pop(context, selected.round()),
              child: const Text('确定'),
            ),
          ],
        ),
      ),
    );
  }

  Future<DateTime?> _pickDateTime(
    DateTime currentUtc,
    String helpText,
  ) async {
    final current = currentUtc.toLocal();
    final date = await showDatePicker(
      context: context,
      firstDate: DateTime(2020),
      lastDate: DateTime.now().add(const Duration(days: 365)),
      initialDate: current,
      helpText: helpText,
    );
    if (date == null || !mounted) return null;

    final time = await showTimePicker(
      context: context,
      initialTime: TimeOfDay.fromDateTime(current),
      helpText: '选择时和分',
      initialEntryMode: TimePickerEntryMode.input,
    );
    if (time == null || !mounted) return null;

    final second = await _pickSecond(current.second);
    if (second == null) return null;

    return DateTime(
      date.year,
      date.month,
      date.day,
      time.hour,
      time.minute,
      second,
    ).toUtc();
  }

  Future<void> _pickStart() async {
    final value = await _pickDateTime(start, '选择开始日期');
    if (value != null) setState(() => start = value);
  }

  Future<void> _pickEnd() async {
    final value = await _pickDateTime(end, '选择结束日期');
    if (value != null) setState(() => end = value);
  }

  Future<void> _useQuickRange(Duration duration) async {
    final now = DateTime.now().toUtc();
    setState(() {
      end = now;
      start = now.subtract(duration);
    });
    await _query();
  }

  Future<void> _query() async {
    if (end.isBefore(start)) {
      setState(() => error = '结束时间不能早于开始时间');
      return;
    }

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
      if (!mounted) return;
      setState(() {
        points = result;
        selectedIndex = result.isEmpty ? 0 : result.length - 1;
      });
    } catch (e) {
      if (mounted) setState(() => error = e.toString());
    } finally {
      if (mounted) setState(() => loading = false);
    }
  }

  void _selectPoint(int index, List<LatLng> displayPoints) {
    setState(() => selectedIndex = index);
    mapController.move(displayPoints[index], mapController.camera.zoom);
  }

  @override
  Widget build(BuildContext context) {
    final displayPoints = points
        .map((point) => CoordinateConverter.wgs84ToGcj02(point.lat, point.lng))
        .toList();
    final center = displayPoints.isNotEmpty
        ? displayPoints.last
        : const LatLng(31.2304, 121.4737);
    final selectedPoint = points.isEmpty ? null : points[selectedIndex];
    final selectedDisplayPoint =
        displayPoints.isEmpty ? null : displayPoints[selectedIndex];
    final preciseFormat = DateFormat('yyyy-MM-dd HH:mm:ss');

    return Scaffold(
      appBar: AppBar(title: const Text('历史轨迹')),
      body: Column(
        children: [
          Container(
            padding: const EdgeInsets.fromLTRB(16, 8, 16, 12),
            color: Theme.of(context).colorScheme.surface,
            child: Column(
              children: [
                SingleChildScrollView(
                  scrollDirection: Axis.horizontal,
                  child: Row(
                    children: [
                      _QuickRangeChip(
                        label: '近5分钟',
                        onPressed: () =>
                            _useQuickRange(const Duration(minutes: 5)),
                      ),
                      _QuickRangeChip(
                        label: '近30分钟',
                        onPressed: () =>
                            _useQuickRange(const Duration(minutes: 30)),
                      ),
                      _QuickRangeChip(
                        label: '近1小时',
                        onPressed: () =>
                            _useQuickRange(const Duration(hours: 1)),
                      ),
                      _QuickRangeChip(
                        label: '近6小时',
                        onPressed: () =>
                            _useQuickRange(const Duration(hours: 6)),
                      ),
                      _QuickRangeChip(
                        label: '近24小时',
                        onPressed: () =>
                            _useQuickRange(const Duration(hours: 24)),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 8),
                Row(
                  children: [
                    Expanded(
                      child: _DateTimeButton(
                        label: '开始',
                        value: preciseFormat.format(start.toLocal()),
                        icon: Icons.first_page,
                        onPressed: _pickStart,
                      ),
                    ),
                    const SizedBox(width: 8),
                    Expanded(
                      child: _DateTimeButton(
                        label: '结束',
                        value: preciseFormat.format(end.toLocal()),
                        icon: Icons.last_page,
                        onPressed: _pickEnd,
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
                    label: Text(loading ? '查询中' : '按秒查询轨迹'),
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
                  mapController: mapController,
                  options: MapOptions(
                    initialCenter: center,
                    initialZoom: 15,
                  ),
                  children: [
                    TileLayer(
                      urlTemplate: AppConfig.mapTileUrlTemplate,
                      subdomains: AppConfig.mapTileSubdomains,
                      userAgentPackageName: AppConfig.androidApplicationId,
                    ),
                    if (displayPoints.isNotEmpty)
                      PolylineLayer(
                        polylines: [
                          Polyline(
                            points: displayPoints,
                            strokeWidth: 5,
                            color: const Color(0xFF176B5B),
                          ),
                        ],
                      ),
                    if (displayPoints.isNotEmpty)
                      MarkerLayer(
                        markers: [
                          Marker(
                            point: displayPoints.first,
                            width: 40,
                            height: 40,
                            child: const Icon(
                              Icons.play_circle_fill,
                              color: Color(0xFF18794E),
                              size: 32,
                            ),
                          ),
                          Marker(
                            point: displayPoints.last,
                            width: 40,
                            height: 40,
                            child: const Icon(
                              Icons.flag_circle,
                              color: Color(0xFFC43D3D),
                              size: 32,
                            ),
                          ),
                          if (selectedDisplayPoint != null)
                            Marker(
                              point: selectedDisplayPoint,
                              width: 48,
                              height: 48,
                              child: Container(
                                decoration: BoxDecoration(
                                  color: Colors.white,
                                  shape: BoxShape.circle,
                                  boxShadow: [
                                    BoxShadow(
                                      color:
                                          Colors.black.withValues(alpha: 0.2),
                                      blurRadius: 8,
                                    ),
                                  ],
                                ),
                                child: const Icon(
                                  Icons.directions_car_filled,
                                  color: Color(0xFF176B5B),
                                ),
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
                if (selectedPoint != null)
                  Positioned(
                    left: 12,
                    right: 12,
                    bottom: 12,
                    child: SafeArea(
                      top: false,
                      child: Material(
                        color: Colors.white,
                        borderRadius: BorderRadius.circular(8),
                        elevation: 3,
                        child: Padding(
                          padding: const EdgeInsets.fromLTRB(12, 10, 12, 8),
                          child: Column(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              Row(
                                children: [
                                  Expanded(
                                    child: Text(
                                      preciseFormat.format(
                                        selectedPoint.utcTime.toLocal(),
                                      ),
                                      style: const TextStyle(
                                        fontWeight: FontWeight.w700,
                                      ),
                                    ),
                                  ),
                                  Text(
                                    '${selectedIndex + 1} / ${points.length}',
                                    style:
                                        const TextStyle(color: Colors.black54),
                                  ),
                                ],
                              ),
                              Slider(
                                value: selectedIndex.toDouble(),
                                min: 0,
                                max: (points.length - 1).toDouble(),
                                divisions:
                                    points.length > 1 && points.length <= 500
                                        ? points.length - 1
                                        : null,
                                onChanged: points.length <= 1
                                    ? null
                                    : (value) => _selectPoint(
                                          value.round(),
                                          displayPoints,
                                        ),
                              ),
                              Row(
                                children: [
                                  Expanded(
                                    child: Text(
                                      '速度 ${selectedPoint.speed.toStringAsFixed(1)} km/h',
                                    ),
                                  ),
                                  Text(
                                    '${selectedPoint.lat.toStringAsFixed(6)}, '
                                    '${selectedPoint.lng.toStringAsFixed(6)}',
                                    style: const TextStyle(fontSize: 12),
                                  ),
                                ],
                              ),
                            ],
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

class _QuickRangeChip extends StatelessWidget {
  final String label;
  final VoidCallback onPressed;

  const _QuickRangeChip({required this.label, required this.onPressed});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(right: 8),
      child: ActionChip(
        avatar: const Icon(Icons.schedule, size: 16),
        label: Text(label),
        onPressed: onPressed,
      ),
    );
  }
}

class _DateTimeButton extends StatelessWidget {
  final String label;
  final String value;
  final IconData icon;
  final VoidCallback onPressed;

  const _DateTimeButton({
    required this.label,
    required this.value,
    required this.icon,
    required this.onPressed,
  });

  @override
  Widget build(BuildContext context) {
    return OutlinedButton(
      onPressed: onPressed,
      style: OutlinedButton.styleFrom(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 9),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
      ),
      child: Row(
        children: [
          Icon(icon, size: 20),
          const SizedBox(width: 7),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(label, style: const TextStyle(fontSize: 11)),
                Text(
                  value,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(
                    fontSize: 12,
                    fontWeight: FontWeight.w700,
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
