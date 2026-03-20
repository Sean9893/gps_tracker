import 'package:flutter/material.dart';
import '../models/models.dart';
import '../services/api_service.dart';
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
  String? error;
  GpsPoint? latest;
  DeviceStatus? status;

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
      final l = await api.fetchLatest(widget.deviceId);
      final s = await api.fetchStatus(widget.deviceId);
      setState(() {
        latest = l;
        status = s;
      });
    } catch (e) {
      setState(() => error = e.toString());
    } finally {
      setState(() => loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text('Device ${widget.deviceId}'),
        actions: [IconButton(onPressed: _load, icon: const Icon(Icons.refresh))],
      ),
      body: loading
          ? const Center(child: CircularProgressIndicator())
          : error != null
              ? Center(child: Text('Request failed: $error'))
              : latest == null
                  ? const Center(child: Text('No latest GPS data'))
                  : Padding(
                      padding: const EdgeInsets.all(12),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text('Device ID: ${widget.deviceId}'),
                          Text('Status: ${(status?.online ?? false) ? "Online" : "Offline"}'),
                          Text('UTC Time: ${latest!.utcTime.toUtc().toIso8601String()}'),
                          Text('Location: ${latest!.lat}, ${latest!.lng}'),
                          Text('Speed: ${latest!.speed}'),
                          Text('Satellites: ${latest!.satellites}'),
                          Text('Fix: ${latest!.fix == 1 ? "Valid" : "Invalid"}'),
                          const SizedBox(height: 16),
                          Row(
                            children: [
                              ElevatedButton(
                                onPressed: () {
                                  Navigator.push(
                                    context,
                                    MaterialPageRoute(
                                      builder: (_) => MapPage(deviceId: widget.deviceId),
                                    ),
                                  );
                                },
                                child: const Text('Live map'),
                              ),
                              const SizedBox(width: 12),
                              ElevatedButton(
                                onPressed: () {
                                  Navigator.push(
                                    context,
                                    MaterialPageRoute(
                                      builder: (_) => HistoryPage(deviceId: widget.deviceId),
                                    ),
                                  );
                                },
                                child: const Text('History'),
                              ),
                            ],
                          ),
                        ],
                      ),
                    ),
    );
  }
}
