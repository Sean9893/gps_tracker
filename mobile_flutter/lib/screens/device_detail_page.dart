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
  bool sendingCommand = false;
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

  Future<void> _sendCommand(String command, String label) async {
    setState(() => sendingCommand = true);
    try {
      await api.sendCommand(deviceId: widget.deviceId, command: command);
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('$label command sent')),
      );
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Command failed: $e')),
      );
    } finally {
      if (mounted) {
        setState(() => sendingCommand = false);
      }
    }
  }

  Widget _commandButton({
    required IconData icon,
    required String label,
    required String command,
  }) {
    return ElevatedButton.icon(
      onPressed: sendingCommand ? null : () => _sendCommand(command, label),
      icon: Icon(icon),
      label: Text(label),
    );
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
                          Center(
                            child: Column(
                              children: [
                                _commandButton(
                                  icon: Icons.keyboard_arrow_up,
                                  label: 'Forward',
                                  command: 'forward',
                                ),
                                const SizedBox(height: 8),
                                Row(
                                  mainAxisAlignment: MainAxisAlignment.center,
                                  children: [
                                    _commandButton(
                                      icon: Icons.keyboard_arrow_left,
                                      label: 'Left',
                                      command: 'left',
                                    ),
                                    const SizedBox(width: 12),
                                    _commandButton(
                                      icon: Icons.keyboard_arrow_right,
                                      label: 'Right',
                                      command: 'right',
                                    ),
                                  ],
                                ),
                                const SizedBox(height: 8),
                                _commandButton(
                                  icon: Icons.keyboard_arrow_down,
                                  label: 'Backward',
                                  command: 'backward',
                                ),
                              ],
                            ),
                          ),
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
