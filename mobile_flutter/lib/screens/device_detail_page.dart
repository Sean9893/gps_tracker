import 'dart:async';

import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

import '../app_config.dart';
import '../models/models.dart';
import '../services/api_service.dart';
import '../widgets/dashboard_tile.dart';
import '../widgets/speed_gauge.dart';
import 'geofence_page.dart';
import 'history_page.dart';
import 'map_page.dart';
import 'remote_control_page.dart';

class DeviceDetailPage extends StatefulWidget {
  final String deviceId;

  const DeviceDetailPage({super.key, required this.deviceId});

  @override
  State<DeviceDetailPage> createState() => _DeviceDetailPageState();
}

class _DeviceDetailPageState extends State<DeviceDetailPage> {
  final api = ApiService();
  bool loading = true;
  String? error;
  GpsPoint? latest;
  DeviceStatus? status;
  GeofenceConfig? fence;
  HealthData? health;
  Timer? healthTimer;
  bool healthRefreshInProgress = false;
  bool statusRefreshInProgress = false;

  @override
  void initState() {
    super.initState();
    _load();
    // 每 2 秒同时刷新健康数据（心率/血氧）和设备状态（含摔倒检测），
    // 保证有人摔倒时"防摔报警"能在页面停留期间自动弹出，而不需要手动下拉刷新。
    healthTimer = Timer.periodic(
      const Duration(seconds: 2),
      (_) {
        _refreshHealth();
        _refreshStatus();
      },
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

  Future<void> _refreshStatus() async {
    if (statusRefreshInProgress) return;
    statusRefreshInProgress = true;
    try {
      final nextStatus = await api.fetchStatus(widget.deviceId);
      if (mounted) setState(() => status = nextStatus);
    } catch (_) {
      // 静默失败，保留上一次已知状态，避免网络抖动时闪烁/误报。
    } finally {
      statusRefreshInProgress = false;
    }
  }

  Future<void> _callEmergencyNumber() async {
    final uri = Uri(scheme: 'tel', path: AppConfig.emergencyPhoneNumber);
    try {
      final ok = await launchUrl(uri);
      if (!ok && mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('无法拨打电话')),
        );
      }
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('拨打电话失败：$e')),
      );
    }
  }


  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        child: loading
            ? const Center(child: CircularProgressIndicator())
            : error != null
                ? _ErrorView(message: error!, onRetry: _load)
                : Column(
                    children: [
                      Expanded(
                        child: RefreshIndicator(
                          onRefresh: _load,
                          child: ListView(
                            padding: const EdgeInsets.fromLTRB(16, 8, 16, 28),
                            children: [
                              _SpeedCard(
                                speedKmh: latest?.speed ?? 0,
                                moving: latest?.moving ?? false,
                                battery: latest?.battery ?? 0,
                                online: status?.online ?? false,
                                onBack: () => Navigator.pop(context),
                                onRefresh: loading ? null : _load,
                              ),
                              const SizedBox(height: 16),
                              _DashboardGrid(
                                children: [
                                  DashboardTile(
                                    icon: Icons.phone_in_talk_outlined,
                                    label: '一键呼叫',
                                    onPressed: _callEmergencyNumber,
                                  ),
                                  DashboardTile(
                                    icon: Icons.location_on_outlined,
                                    label: 'GPS定位',
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
                                  DashboardTile(
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
                                  DashboardTile(
                                    icon: Icons.route_outlined,
                                    label: '行驶轨迹',
                                    onPressed: () => Navigator.push(
                                      context,
                                      MaterialPageRoute(
                                        builder: (_) => HistoryPage(
                                          deviceId: widget.deviceId,
                                        ),
                                      ),
                                    ),
                                  ),
                                  DashboardTile(
                                    icon: Icons.games_outlined,
                                    label: '遥控',
                                    onPressed: () => Navigator.push(
                                      context,
                                      MaterialPageRoute(
                                        builder: (_) => RemoteControlPage(
                                          deviceId: widget.deviceId,
                                        ),
                                      ),
                                    ),
                                  ),
                                  DashboardTile(
                                    icon: Icons.warning_outlined,
                                    label: '防摔报警',
                                    alert: status?.fallDetected ?? false,
                                    onPressed: null,
                                  ),
                                  DashboardTile(
                                    icon: Icons.favorite_outline,
                                    label: '健康',
                                    subtitle: health == null
                                        ? '加载中...'
                                        : '${health!.heartRateText} | ${health!.spo2Text}',
                                    onPressed: null,
                                  ),
                                ],
                              ),
                            ],
                          ),
                        ),
                      ),
                    ],
                  ),
      ),
    );
  }
}

class _SpeedCard extends StatelessWidget {
  final double speedKmh;
  final bool moving;
  final int battery;
  final bool online;
  final VoidCallback onBack;
  final VoidCallback? onRefresh;

  const _SpeedCard({
    required this.speedKmh,
    required this.moving,
    required this.battery,
    required this.online,
    required this.onBack,
    required this.onRefresh,
  });

  @override
  Widget build(BuildContext context) {
    const gaugeSize = 108.0;
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(10),
      decoration: BoxDecoration(
        gradient: const LinearGradient(
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
          colors: [Color(0xFF4FA890), Color(0xFF7DCCB8), Color(0xFFE8F5F1)],
          stops: [0.0, 0.5, 1.0],
        ),
        borderRadius: BorderRadius.circular(14),
      ),
      child: Stack(
        children: [
          Column(
            children: [
              const SizedBox(height: 30),
              Row(
                crossAxisAlignment: CrossAxisAlignment.center,
                children: [
                  Expanded(
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        // 品牌名称和在线状态
                        Stack(
                          clipBehavior: Clip.none,
                          children: [
                            Container(
                              padding: const EdgeInsets.symmetric(
                                  horizontal: 16, vertical: 6),
                              decoration: BoxDecoration(
                                color: const Color(0xFF176B5B),
                                borderRadius: BorderRadius.circular(999),
                                boxShadow: [
                                  BoxShadow(
                                    color: const Color(0xFF176B5B)
                                        .withValues(alpha: 0.25),
                                    blurRadius: 4,
                                    offset: const Offset(0, 1),
                                  ),
                                ],
                              ),
                              child: const Text(
                                '耐心 Nysin',
                                style: TextStyle(
                                  color: Colors.white,
                                  fontSize: 12,
                                  fontWeight: FontWeight.w700,
                                  letterSpacing: 0.3,
                                ),
                              ),
                            ),
                            Positioned(
                              top: -2,
                              right: -2,
                              child: Container(
                                width: 10,
                                height: 10,
                                decoration: BoxDecoration(
                                  color: online
                                      ? const Color(0xFF4CAF50)
                                      : const Color(0xFF9E9E9E),
                                  shape: BoxShape.circle,
                                  border: Border.all(
                                      color: Colors.white, width: 1.5),
                                  boxShadow: [
                                    BoxShadow(
                                      color: (online
                                              ? const Color(0xFF4CAF50)
                                              : const Color(0xFF9E9E9E))
                                          .withValues(alpha: 0.5),
                                      blurRadius: 2,
                                      spreadRadius: 0.5,
                                    ),
                                  ],
                                ),
                              ),
                            ),
                          ],
                        ),
                        const SizedBox(height: 10),
                        Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Container(
                              width: 14,
                              height: 14,
                              decoration: BoxDecoration(
                                shape: BoxShape.circle,
                                border: Border.all(
                                  color: Colors.white.withValues(alpha: 0.8),
                                  width: 1.5,
                                ),
                              ),
                              child: const Center(
                                child: Icon(Icons.remove,
                                    color: Colors.white70, size: 9),
                              ),
                            ),
                            const SizedBox(width: 5),
                            Text(
                              moving ? '运动' : '停止',
                              style: const TextStyle(
                                color: Colors.white70,
                                fontSize: 12,
                                fontWeight: FontWeight.w500,
                              ),
                            ),
                          ],
                        ),
                      ],
                    ),
                  ),
                  SpeedGauge(
                    speedKmh: speedKmh,
                    moving: moving,
                    size: gaugeSize,
                  ),
                ],
              ),
              const Row(
                children: [
                  Expanded(child: SizedBox()),
                  SizedBox(
                    width: gaugeSize,
                    child: Text(
                      'km/h',
                      textAlign: TextAlign.center,
                      style: TextStyle(
                        color: Color(0xFF176B5B),
                        fontSize: 11,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 6),
              Row(
                children: [
                  const Icon(Icons.battery_charging_full,
                      color: Color(0xFF176B5B), size: 17),
                  const SizedBox(width: 5),
                  Text(
                    '电量 $battery%',
                    style: const TextStyle(
                      color: Color(0xFF176B5B),
                      fontSize: 12,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: ClipRRect(
                      borderRadius: BorderRadius.circular(3),
                      child: LinearProgressIndicator(
                        value: battery / 100.0,
                        minHeight: 6,
                        backgroundColor: Colors.white.withValues(alpha: 0.5),
                        valueColor: const AlwaysStoppedAnimation<Color>(
                          Color(0xFF176B5B),
                        ),
                      ),
                    ),
                  ),
                ],
              ),
            ],
          ),
          // 左上角返回按钮
          Positioned(
            top: 0,
            left: 0,
            child: Material(
              color: Colors.transparent,
              child: InkWell(
                onTap: onBack,
                borderRadius: BorderRadius.circular(20),
                child: Container(
                  padding: const EdgeInsets.all(6),
                  child: const Icon(
                    Icons.arrow_back,
                    color: Colors.white,
                    size: 22,
                  ),
                ),
              ),
            ),
          ),
          // 右上角刷新按钮
          Positioned(
            top: 0,
            right: 0,
            child: Material(
              color: Colors.transparent,
              child: InkWell(
                onTap: onRefresh,
                borderRadius: BorderRadius.circular(20),
                child: Container(
                  padding: const EdgeInsets.all(6),
                  child: Icon(
                    Icons.refresh,
                    color: onRefresh == null ? Colors.white38 : Colors.white,
                    size: 22,
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

class _DashboardGrid extends StatelessWidget {
  final List<Widget> children;

  const _DashboardGrid({required this.children});

  @override
  Widget build(BuildContext context) {
    return Stack(
      children: [
        GridView.count(
          crossAxisCount: 2,
          shrinkWrap: true,
          physics: const NeverScrollableScrollPhysics(),
          mainAxisSpacing: 12,
          crossAxisSpacing: 12,
          childAspectRatio: 1.35,
          children: children,
        ),
        Positioned(
          left: 0,
          right: 0,
          top: 0,
          bottom: 0,
          child: Center(
            child: Container(
              width: 10,
              height: 10,
              decoration: BoxDecoration(
                color: const Color(0xFF176B5B),
                shape: BoxShape.circle,
                boxShadow: [
                  BoxShadow(
                    color: const Color(0xFF176B5B).withValues(alpha: 0.25),
                    blurRadius: 4,
                    spreadRadius: 1,
                  ),
                ],
              ),
            ),
          ),
        ),
      ],
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
