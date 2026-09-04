import 'dart:async';

import 'package:flutter/material.dart';

import '../services/api_service.dart';
import '../widgets/joystick_pad.dart';

/// 独立的遥控页面，只负责轮椅的远程摇杆操控。
class RemoteControlPage extends StatefulWidget {
  final String deviceId;

  const RemoteControlPage({super.key, required this.deviceId});

  @override
  State<RemoteControlPage> createState() => _RemoteControlPageState();
}

class _RemoteControlPageState extends State<RemoteControlPage> {
  final api = ApiService();

  Timer? _joystickThrottleTimer;
  bool _joystickDragging = false;
  bool _joystickSending = false;
  int _joystickX = kJoystickCenter;
  int _joystickY = kJoystickCenter;

  @override
  void dispose() {
    _joystickThrottleTimer?.cancel();
    super.dispose();
  }

  // 摇杆拖动中持续回调：记录最新坐标，并在拖动开始时启动节流定时器，
  // 每隔 150ms 发送一次最新的摇杆坐标，避免请求过于频繁。
  void _onJoystickChanged(int x, int y) {
    _joystickX = x;
    _joystickY = y;
    if (!_joystickDragging) {
      _joystickDragging = true;
      unawaited(_sendJoystickNow());
      _joystickThrottleTimer = Timer.periodic(
        const Duration(milliseconds: 150),
        (_) => _sendJoystickNow(),
      );
    }
  }

  // 松手回中：停止节流定时器，并发送一次居中坐标，确保小车停止。
  void _onJoystickReleased() {
    _joystickThrottleTimer?.cancel();
    _joystickThrottleTimer = null;
    _joystickDragging = false;
    _joystickX = kJoystickCenter;
    _joystickY = kJoystickCenter;
    unawaited(_sendJoystickNow());
  }

  Future<void> _sendJoystickNow() async {
    if (_joystickSending) return;
    _joystickSending = true;
    final x = _joystickX;
    final y = _joystickY;
    try {
      await api.sendJoystick(deviceId: widget.deviceId, x: x, y: y);
    } catch (_) {
      // 摇杆连续发送期间静默失败，避免刷屏提示；网络异常会在下次操作时体现。
    } finally {
      _joystickSending = false;
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('遥控轮椅'),
        centerTitle: true,
      ),
      body: SafeArea(
        child: Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              const Icon(
                Icons.accessible,
                size: 80,
                color: Color(0xFF176B5B),
              ),
              const SizedBox(height: 16),
              Text(
                '设备 ${widget.deviceId}',
                style: const TextStyle(
                  fontSize: 18,
                  fontWeight: FontWeight.w600,
                  color: Color(0xFF176B5B),
                ),
              ),
              const SizedBox(height: 8),
              const Text(
                '拖动摇杆控制轮椅方向',
                style: TextStyle(
                  fontSize: 14,
                  color: Colors.black54,
                ),
              ),
              const SizedBox(height: 40),
              JoystickPad(
                size: 220,
                onChanged: _onJoystickChanged,
                onReleased: _onJoystickReleased,
              ),
            ],
          ),
        ),
      ),
    );
  }
}
