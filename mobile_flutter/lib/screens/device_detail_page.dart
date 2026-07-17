import 'dart:async';

import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../models/models.dart';
import '../services/api_service.dart';
import '../widgets/wheelchair_icon.dart';
import 'geofence_page.dart';
import 'history_page.dart';
import 'map_page.dart';

class DeviceDetailPage extends StatefulWidget {
  final String deviceId;

  const DeviceDetailPage({super.key, required this.deviceId});

  @override
  State<DeviceDetailPage> createState() => _DeviceDetailPageState();
}

class _DeviceDetailPageState extends State<DeviceDetailPage> {
  final api = ApiService();
  bool loading = true;
  bool sendingCommand = false;
  String? error;
  GpsPoint? latest;
  DeviceStatus? status;
  GeofenceConfig? fence;
  HealthData? health;
  Timer? healthTimer;
  bool healthRefreshInProgress = false;

  @override
  void initState() {
    super.initState();
    _load();
    healthTimer = Timer.periodic(
      const Duration(seconds: 2),
      (_) => _refreshHealth(),
    );
  }

  @override
  void dispose() {
    healthTimer?.cancel();
    super.dispose();
  }

  Future<void> _load() async {
    setState(() {
      loading = true;
      error = null;
    });
    try {
      final results = await Future.wait([
        api.fetchLatest(widget.deviceId),
        api.fetchStatus(widget.deviceId),
        api.fetchGeofence(widget.deviceId),
      ]);
      if (!mounted) return;
      setState(() {
        latest = results[0] as GpsPoint?;
        status = results[1] as DeviceStatus;
        fence = results[2] as GeofenceConfig;
      });
      unawaited(_refreshHealth());
    } catch (e) {
      if (mounted) setState(() => error = e.toString());
    } finally {
      if (mounted) setState(() => loading = false);
    }
  }

  Future<void> _refreshHealth() async {
    if (healthRefreshInProgress) return;
    healthRefreshInProgress = true;
    try {
      final nextHealth = await api.fetchLatestHealth(widget.deviceId);
      if (mounted) setState(() => health = nextHealth);
    } catch (_) {
      if (mounted) setState(() => health = null);
    } finally {
      healthRefreshInProgress = false;
    }
  }

  Future<void> _sendCommand(String command, String label) async {
    setState(() => sendingCommand = true);
    try {
      await api.sendCommand(deviceId: widget.deviceId, command: command);
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('已发送：$label')),
      );
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('指令发送失败：$e')),
      );
    } finally {
      if (mounted) setState(() => sendingCommand = false);
    }
  }

  String _formatTime(DateTime value) {
    return DateFormat('yyyy年MM月dd日 HH:mm:ss').format(value.toLocal());
  }

  String _fenceText() {
    if (!(fence?.configured ?? false)) return '未设置';
    if (!(fence?.enabled ?? false)) return '已停用';
    if (fence?.inside == true) return '围栏内';
    if (fence?.inside == false) return '围栏外';
    return '等待定位';
  }

  Color _fenceColor() {
    if (fence?.inside == false && fence?.enabled == true) {
      return const Color(0xFFC43D3D);
    }
    if (fence?.inside == true && fence?.enabled == true) {
      return const Color(0xFF18794E);
    }
    return const Color(0xFF6D7472);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(widget.deviceId),
        actions: [
          IconButton(
            tooltip: '刷新',
            onPressed: loading ? null : _load,
            icon: const Icon(Icons.refresh),
          ),
        ],
      ),
      body: loading
          ? const Center(child: CircularProgressIndicator())
          : error != null
              ? _ErrorView(message: error!, onRetry: _load)
              : RefreshIndicator(
                  onRefresh: _load,
                  child: ListView(
                    padding: const EdgeInsets.fromLTRB(16, 8, 16, 28),
                    children: [
                      _StatusHeader(
                        online: status?.online ?? false,
                        deviceId: widget.deviceId,
                        fenceText: _fenceText(),
                        fenceColor: _fenceColor(),
                      ),
                      const SizedBox(height: 18),
                      const _SectionTitle(title: '轮椅状态'),
                      const SizedBox(height: 10),
                      if (latest == null)
                        const _Notice(
                          icon: Icons.location_off_outlined,
                          text: '暂时没有定位数据，控制功能仍可使用。',
                        )
                      else
                        _LocationSummary(
                          latest: latest!,
                          online: status?.online ?? false,
                          formattedTime: _formatTime(latest!.utcTime),
                        ),
                      const SizedBox(height: 14),
                      HealthSummaryCard(health: health),
                      const SizedBox(height: 22),
                      const _SectionTitle(title: '方向控制'),
                      const SizedBox(height: 6),
                      const Text(
                        '点击方向键向轮椅发送一次控制指令',
                        style: TextStyle(color: Colors.black54, fontSize: 13),
                      ),
                      const SizedBox(height: 14),
                      _DirectionPad(
                        disabled: sendingCommand,
                        onCommand: _sendCommand,
                      ),
                      const SizedBox(height: 24),
                      const _SectionTitle(title: '功能'),
                      const SizedBox(height: 10),
                      Row(
                        children: [
                          Expanded(
                            child: _FeatureButton(
                              icon: Icons.map_outlined,
                              label: '实时地图',
                              onPressed: latest == null
                                  ? null
                                  : () => Navigator.push(
                                        context,
                                        MaterialPageRoute(
                                          builder: (_) => MapPage(
                                            deviceId: widget.deviceId,
                                          ),
                                        ),
                                      ),
                            ),
                          ),
                          const SizedBox(width: 10),
                          Expanded(
                            child: _FeatureButton(
                              icon: Icons.route_outlined,
                              label: '历史轨迹',
                              onPressed: () => Navigator.push(
                                context,
                                MaterialPageRoute(
                                  builder: (_) => HistoryPage(
                                    deviceId: widget.deviceId,
                                  ),
                                ),
                              ),
                            ),
                          ),
                          const SizedBox(width: 10),
                          Expanded(
                            child: _FeatureButton(
                              icon: Icons.shield_outlined,
                              label: '电子围栏',
                              alert: fence?.inside == false &&
                                  fence?.enabled == true,
                              onPressed: () async {
                                await Navigator.push(
                                  context,
                                  MaterialPageRoute(
                                    builder: (_) => GeofencePage(
                                      deviceId: widget.deviceId,
                                    ),
                                  ),
                                );
                                _load();
                              },
                            ),
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
    );
  }
}

class HealthSummaryCard extends StatelessWidget {
  final HealthData? health;

  const HealthSummaryCard({super.key, required this.health});

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Row(
          children: [
            Expanded(
              child: _Metric(
                icon: Icons.favorite_outline,
                value: health?.heartRateText ?? '——',
                label: '心率',
              ),
            ),
            Expanded(
              child: _Metric(
                icon: Icons.water_drop_outlined,
                value: health?.spo2Text ?? '——',
                label: '血氧',
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _StatusHeader extends StatelessWidget {
  final bool online;
  final String deviceId;
  final String fenceText;
  final Color fenceColor;

  const _StatusHeader({
    required this.online,
    required this.deviceId,
    required this.fenceText,
    required this.fenceColor,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: online ? const Color(0xFF176B5B) : const Color(0xFF626967),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Row(
        children: [
          const WheelchairIcon(size: 52, padding: 3),
          const SizedBox(width: 14),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  online ? '轮椅在线' : '轮椅离线',
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 20,
                    fontWeight: FontWeight.w700,
                  ),
                ),
                Text(
                  '设备编号 $deviceId',
                  style: const TextStyle(color: Colors.white70),
                ),
              ],
            ),
          ),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 5),
            decoration: BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.circular(999),
            ),
            child: Text(
              fenceText,
              style: TextStyle(
                color: fenceColor,
                fontSize: 12,
                fontWeight: FontWeight.w700,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _LocationSummary extends StatelessWidget {
  final GpsPoint latest;
  final bool online;
  final String formattedTime;

  const _LocationSummary({
    required this.latest,
    required this.online,
    required this.formattedTime,
  });

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(
          children: [
            Row(
              children: [
                Expanded(
                  child: _Metric(
                    icon: latest.moving
                        ? Icons.motion_photos_on_outlined
                        : Icons.pause_circle_outline,
                    value: latest.moving ? '运动' : '静止',
                    label:
                        '位移 ${latest.movementDistanceM.toStringAsFixed(1)} 米',
                  ),
                ),
                Expanded(
                  child: _Metric(
                    icon: Icons.satellite_alt_outlined,
                    value: '${online ? 8 : 0}',
                    label: '卫星数量',
                  ),
                ),
                Expanded(
                  child: _Metric(
                    icon: latest.fix == 1
                        ? Icons.gps_fixed
                        : Icons.gps_off_outlined,
                    value: latest.fix == 1 ? '有效' : '无效',
                    label: '定位状态',
                  ),
                ),
              ],
            ),
            const Divider(height: 24),
            Row(
              children: [
                const Icon(Icons.location_on_outlined, color: Colors.black54),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    '${latest.lat.toStringAsFixed(6)}, ${latest.lng.toStringAsFixed(6)}',
                  ),
                ),
              ],
            ),
            const SizedBox(height: 8),
            Row(
              children: [
                const Icon(Icons.schedule, color: Colors.black54),
                const SizedBox(width: 8),
                Text(formattedTime),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

class _Metric extends StatelessWidget {
  final IconData icon;
  final String value;
  final String label;

  const _Metric({
    required this.icon,
    required this.value,
    required this.label,
  });

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Icon(icon, color: const Color(0xFF176B5B)),
        const SizedBox(height: 5),
        Text(value, style: const TextStyle(fontWeight: FontWeight.w700)),
        Text(
          label,
          style: const TextStyle(color: Colors.black54, fontSize: 12),
        ),
      ],
    );
  }
}

class _DirectionPad extends StatelessWidget {
  final bool disabled;
  final Future<void> Function(String command, String label) onCommand;

  const _DirectionPad({
    required this.disabled,
    required this.onCommand,
  });

  Widget _button(IconData icon, String label, String command) {
    return SizedBox(
      width: 78,
      height: 64,
      child: FilledButton(
        onPressed: disabled ? null : () => onCommand(command, label),
        style: FilledButton.styleFrom(
          padding: EdgeInsets.zero,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(8),
          ),
        ),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(icon, size: 28),
            Text(label, style: const TextStyle(fontSize: 12)),
          ],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Column(
        children: [
          _button(Icons.keyboard_arrow_up, '前进', 'forward'),
          const SizedBox(height: 8),
          Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              _button(Icons.keyboard_arrow_left, '左转', 'left'),
              const SizedBox(width: 8),
              Container(
                width: 62,
                height: 64,
                decoration: BoxDecoration(
                  color: const Color(0xFFE6EAE8),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: disabled
                    ? const Padding(
                        padding: EdgeInsets.all(20),
                        child: CircularProgressIndicator(strokeWidth: 2),
                      )
                    : const Center(
                        child: WheelchairIcon(size: 54, padding: 2),
                      ),
              ),
              const SizedBox(width: 8),
              _button(Icons.keyboard_arrow_right, '右转', 'right'),
            ],
          ),
          const SizedBox(height: 8),
          _button(Icons.keyboard_arrow_down, '后退', 'backward'),
        ],
      ),
    );
  }
}

class _FeatureButton extends StatelessWidget {
  final IconData icon;
  final String label;
  final VoidCallback? onPressed;
  final bool alert;

  const _FeatureButton({
    required this.icon,
    required this.label,
    required this.onPressed,
    this.alert = false,
  });

  @override
  Widget build(BuildContext context) {
    final color = alert ? const Color(0xFFC43D3D) : const Color(0xFF176B5B);
    return OutlinedButton(
      onPressed: onPressed,
      style: OutlinedButton.styleFrom(
        minimumSize: const Size.fromHeight(74),
        padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 10),
        side: BorderSide(color: color.withValues(alpha: 0.35)),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
      ),
      child: Column(
        children: [
          Icon(icon, color: color),
          const SizedBox(height: 5),
          Text(label, style: TextStyle(color: color, fontSize: 13)),
        ],
      ),
    );
  }
}

class _SectionTitle extends StatelessWidget {
  final String title;

  const _SectionTitle({required this.title});

  @override
  Widget build(BuildContext context) {
    return Text(
      title,
      style: const TextStyle(fontSize: 17, fontWeight: FontWeight.w700),
    );
  }
}

class _Notice extends StatelessWidget {
  final IconData icon;
  final String text;

  const _Notice({required this.icon, required this.text});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: const Color(0xFFFFF4D6),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Row(
        children: [
          Icon(icon, color: const Color(0xFF8A5A00)),
          const SizedBox(width: 10),
          Expanded(child: Text(text)),
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
