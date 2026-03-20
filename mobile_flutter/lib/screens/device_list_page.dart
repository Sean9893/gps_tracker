import 'package:flutter/material.dart';
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
      setState(() => devices = result);
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
        title: const Text('Devices'),
        actions: [
          IconButton(onPressed: _load, icon: const Icon(Icons.refresh)),
        ],
      ),
      body: loading
          ? const Center(child: CircularProgressIndicator())
          : error != null
              ? Center(child: Text('Network error: $error'))
              : devices.isEmpty
                  ? const Center(child: Text('No devices available'))
                  : ListView.builder(
                      itemCount: devices.length,
                      itemBuilder: (_, i) {
                        final d = devices[i];
                        return ListTile(
                          title: Text(d.deviceId),
                          subtitle: Text('Last update: ${d.lastOnlineTime ?? "-"}'),
                          trailing: Text(
                            d.online ? 'Online' : 'Offline',
                            style: TextStyle(color: d.online ? Colors.green : Colors.red),
                          ),
                          onTap: () {
                            Navigator.push(
                              context,
                              MaterialPageRoute(
                                builder: (_) => DeviceDetailPage(deviceId: d.deviceId),
                              ),
                            );
                          },
                        );
                      },
                    ),
    );
  }
}
