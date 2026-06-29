import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../models/models.dart';
import '../services/api_service.dart';
import 'device_detail_page.dart';

class DeviceListPage extends StatefulWidget {
  const DeviceListPage({super.key});

  @override
  State<DeviceListPage> createState() => _DeviceListPageState();
}

class _DeviceListPageState extends State<DeviceListPage> {
  final api = ApiService();
  bool loading = true;
  String? error;
  List<DeviceSummary> devices = [];

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
      final result = await api.fetchDevices();
      if (mounted) setState(() => devices = result);
    } catch (e) {
      if (mounted) setState(() => error = e.toString());
    } finally {
      if (mounted) setState(() => loading = false);
    }
  }

  String _formatTime(String? value) {
    if (value == null) return '暂无上报';
    try {
      return DateFormat('MM月dd日 HH:mm').format(DateTime.parse(value).toLocal());
    } catch (_) {
      return value;
    }
  }

  @override
  Widget build(BuildContext context) {
    final onlineCount = devices.where((device) => device.online).length;

    return Scaffold(
      appBar: AppBar(
        title: const Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('车辆定位', style: TextStyle(fontWeight: FontWeight.w700)),
            Text(
              '设备状态与远程控制',
              style: TextStyle(fontSize: 12, fontWeight: FontWeight.normal),
            ),
          ],
        ),
        actions: [
          IconButton(
            tooltip: '刷新',
            onPressed: loading ? null : _load,
            icon: const Icon(Icons.refresh),
          ),
          const SizedBox(width: 4),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: _load,
        child: loading && devices.isEmpty
            ? const Center(child: CircularProgressIndicator())
            : error != null && devices.isEmpty
                ? _EmptyState(
                    icon: Icons.cloud_off,
                    title: '暂时无法连接服务器',
                    subtitle: error!,
                    buttonText: '重新加载',
                    onPressed: _load,
                  )
                : ListView(
                    padding: const EdgeInsets.fromLTRB(16, 8, 16, 24),
                    children: [
                      Container(
                        padding: const EdgeInsets.all(16),
                        decoration: BoxDecoration(
                          color: const Color(0xFF176B5B),
                          borderRadius: BorderRadius.circular(8),
                        ),
                        child: Row(
                          children: [
                            const Icon(
                              Icons.directions_car_filled,
                              size: 34,
                              color: Colors.white,
                            ),
                            const SizedBox(width: 14),
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text(
                                    '${devices.length} 台设备',
                                    style: const TextStyle(
                                      color: Colors.white,
                                      fontSize: 21,
                                      fontWeight: FontWeight.w700,
                                    ),
                                  ),
                                  Text(
                                    '$onlineCount 台在线',
                                    style: const TextStyle(
                                      color: Color(0xFFD7F0EA),
                                    ),
                                  ),
                                ],
                              ),
                            ),
                            if (loading)
                              const SizedBox(
                                width: 22,
                                height: 22,
                                child: CircularProgressIndicator(
                                  color: Colors.white,
                                  strokeWidth: 2,
                                ),
                              ),
                          ],
                        ),
                      ),
                      const SizedBox(height: 16),
                      if (devices.isEmpty)
                        _EmptyState(
                          icon: Icons.location_off_outlined,
                          title: '还没有设备',
                          subtitle: '设备首次上传定位后会显示在这里。',
                          buttonText: '刷新',
                          onPressed: _load,
                        )
                      else
                        ...devices.map(
                          (device) => Padding(
                            padding: const EdgeInsets.only(bottom: 10),
                            child: Card(
                              child: InkWell(
                                borderRadius: BorderRadius.circular(8),
                                onTap: () async {
                                  await Navigator.push(
                                    context,
                                    MaterialPageRoute(
                                      builder: (_) => DeviceDetailPage(
                                        deviceId: device.deviceId,
                                      ),
                                    ),
                                  );
                                  _load();
                                },
                                child: Padding(
                                  padding: const EdgeInsets.all(14),
                                  child: Row(
                                    children: [
                                      Container(
                                        width: 46,
                                        height: 46,
                                        decoration: BoxDecoration(
                                          color: device.online
                                              ? const Color(0xFFE0F3EC)
                                              : const Color(0xFFE9ECEB),
                                          borderRadius:
                                              BorderRadius.circular(8),
                                        ),
                                        child: Icon(
                                          Icons.directions_car_filled,
                                          color: device.online
                                              ? const Color(0xFF176B5B)
                                              : Colors.grey,
                                        ),
                                      ),
                                      const SizedBox(width: 12),
                                      Expanded(
                                        child: Column(
                                          crossAxisAlignment:
                                              CrossAxisAlignment.start,
                                          children: [
                                            Text(
                                              device.deviceName.isEmpty
                                                  ? device.deviceId
                                                  : device.deviceName,
                                              style: const TextStyle(
                                                fontSize: 16,
                                                fontWeight: FontWeight.w700,
                                              ),
                                            ),
                                            const SizedBox(height: 3),
                                            Text(
                                              '编号 ${device.deviceId}',
                                              style: const TextStyle(
                                                color: Colors.black54,
                                                fontSize: 13,
                                              ),
                                            ),
                                            Text(
                                              '最近上报 ${_formatTime(device.lastOnlineTime)}',
                                              style: const TextStyle(
                                                color: Colors.black54,
                                                fontSize: 13,
                                              ),
                                            ),
                                          ],
                                        ),
                                      ),
                                      Column(
                                        crossAxisAlignment:
                                            CrossAxisAlignment.end,
                                        children: [
                                          _StatusBadge(
                                            online: device.online,
                                          ),
                                          const SizedBox(height: 10),
                                          const Icon(
                                            Icons.chevron_right,
                                            color: Colors.black38,
                                          ),
                                        ],
                                      ),
                                    ],
                                  ),
                                ),
                              ),
                            ),
                          ),
                        ),
                    ],
                  ),
      ),
    );
  }
}

class _StatusBadge extends StatelessWidget {
  final bool online;

  const _StatusBadge({required this.online});

  @override
  Widget build(BuildContext context) {
    final color = online ? const Color(0xFF18794E) : const Color(0xFF6D7472);
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 4),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(999),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Container(
            width: 7,
            height: 7,
            decoration: BoxDecoration(color: color, shape: BoxShape.circle),
          ),
          const SizedBox(width: 5),
          Text(
            online ? '在线' : '离线',
            style: TextStyle(
              color: color,
              fontSize: 12,
              fontWeight: FontWeight.w700,
            ),
          ),
        ],
      ),
    );
  }
}

class _EmptyState extends StatelessWidget {
  final IconData icon;
  final String title;
  final String subtitle;
  final String buttonText;
  final VoidCallback onPressed;

  const _EmptyState({
    required this.icon,
    required this.title,
    required this.subtitle,
    required this.buttonText,
    required this.onPressed,
  });

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 64, horizontal: 24),
      child: Column(
        children: [
          Icon(icon, size: 52, color: Colors.black38),
          const SizedBox(height: 14),
          Text(
            title,
            style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w700),
          ),
          const SizedBox(height: 6),
          Text(
            subtitle,
            textAlign: TextAlign.center,
            style: const TextStyle(color: Colors.black54),
          ),
          const SizedBox(height: 18),
          FilledButton.icon(
            onPressed: onPressed,
            icon: const Icon(Icons.refresh),
            label: Text(buttonText),
          ),
        ],
      ),
    );
  }
}
