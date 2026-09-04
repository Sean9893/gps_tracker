import 'package:flutter/gestures.dart';
import 'package:flutter/material.dart';

import 'wheelchair_icon.dart';

/// Joystick axis range: 0-1023 with 512 as the resting/center value.
const int kJoystickMin = 0;
const int kJoystickMax = 1023;
const int kJoystickCenter = 512;

/// A draggable joystick control that reports its position as integer axis
/// values in the range [kJoystickMin, kJoystickMax], with
/// [kJoystickCenter] as the resting/center value.
///
/// - Dragging up increases `y` toward [kJoystickMax]; dragging down
///   decreases it toward [kJoystickMin].
/// - Dragging right increases `x` toward [kJoystickMax]; dragging left
///   decreases it toward [kJoystickMin].
///
/// The knob springs back to the center when released, firing [onChanged]
/// one final time with (512, 512), followed by [onReleased].
class JoystickPad extends StatefulWidget {
  final double size;
  final bool disabled;
  final void Function(int x, int y) onChanged;
  final VoidCallback? onReleased;

  const JoystickPad({
    super.key,
    this.size = 180,
    this.disabled = false,
    required this.onChanged,
    this.onReleased,
  });

  @override
  State<JoystickPad> createState() => _JoystickPadState();
}

class _JoystickPadState extends State<JoystickPad> {
  Offset _knobOffset = Offset.zero;

  double get _knobRadius => widget.size * 0.22;
  double get _travelRadius => widget.size / 2 - _knobRadius;

  void _updateFromLocalPosition(Offset localPosition) {
    final center = Offset(widget.size / 2, widget.size / 2);
    var delta = localPosition - center;
    final distance = delta.distance;
    if (_travelRadius > 0 && distance > _travelRadius) {
      delta = delta / distance * _travelRadius;
    }
    setState(() => _knobOffset = delta);
    _reportValue(delta);
  }

  void _reportValue(Offset delta) {
    final nx = _travelRadius <= 0
        ? 0.0
        : (delta.dx / _travelRadius).clamp(-1.0, 1.0);
    final ny = _travelRadius <= 0
        ? 0.0
        : (delta.dy / _travelRadius).clamp(-1.0, 1.0);
    // Screen dy grows downward; pushing up should increase the joystick y.
    widget.onChanged(_mapAxis(nx), _mapAxis(-ny));
  }

  int _mapAxis(double normalized) {
    final n = normalized.clamp(-1.0, 1.0);
    final value = n >= 0
        ? kJoystickCenter + n * (kJoystickMax - kJoystickCenter)
        : kJoystickCenter + n * (kJoystickCenter - kJoystickMin);
    return value.round().clamp(kJoystickMin, kJoystickMax);
  }

  void _reset() {
    setState(() => _knobOffset = Offset.zero);
    widget.onChanged(kJoystickCenter, kJoystickCenter);
    widget.onReleased?.call();
  }

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      behavior: HitTestBehavior.opaque,
      dragStartBehavior: DragStartBehavior.down,
      onPanStart: widget.disabled
          ? null
          : (details) => _updateFromLocalPosition(details.localPosition),
      onPanUpdate: widget.disabled
          ? null
          : (details) => _updateFromLocalPosition(details.localPosition),
      onPanEnd: widget.disabled ? null : (_) => _reset(),
      onPanCancel: widget.disabled ? null : _reset,
      child: SizedBox(
        width: widget.size,
        height: widget.size,
        child: Stack(
          alignment: Alignment.center,
          children: [
            // 底盘
            Container(
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: const Color(0xFFE8F5F1),
                border: Border.all(
                  color: const Color(0xFFB8E6D5),
                  width: 2,
                ),
              ),
            ),
            // 方向提示箭头
            Align(
              alignment: Alignment.topCenter,
              child: Padding(
                padding: const EdgeInsets.all(10),
                child: Icon(Icons.keyboard_arrow_up,
                    color: const Color(0xFF176B5B).withValues(alpha: 0.35),
                    size: 20),
              ),
            ),
            Align(
              alignment: Alignment.bottomCenter,
              child: Padding(
                padding: const EdgeInsets.all(10),
                child: Icon(Icons.keyboard_arrow_down,
                    color: const Color(0xFF176B5B).withValues(alpha: 0.35),
                    size: 20),
              ),
            ),
            Align(
              alignment: Alignment.centerLeft,
              child: Padding(
                padding: const EdgeInsets.all(10),
                child: Icon(Icons.keyboard_arrow_left,
                    color: const Color(0xFF176B5B).withValues(alpha: 0.35),
                    size: 20),
              ),
            ),
            Align(
              alignment: Alignment.centerRight,
              child: Padding(
                padding: const EdgeInsets.all(10),
                child: Icon(Icons.keyboard_arrow_right,
                    color: const Color(0xFF176B5B).withValues(alpha: 0.35),
                    size: 20),
              ),
            ),
            // 摇杆手柄
            Transform.translate(
              offset: _knobOffset,
              child: Container(
                width: _knobRadius * 2,
                height: _knobRadius * 2,
                alignment: Alignment.center,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color: const Color(0xFF176B5B),
                  boxShadow: [
                    BoxShadow(
                      color: Colors.black.withValues(alpha: 0.25),
                      blurRadius: 6,
                      offset: const Offset(0, 3),
                    ),
                  ],
                ),
                child: widget.disabled
                    ? const SizedBox(
                        width: 20,
                        height: 20,
                        child: CircularProgressIndicator(
                          strokeWidth: 2,
                          valueColor: AlwaysStoppedAnimation(Colors.white),
                        ),
                      )
                    : WheelchairIcon(
                        size: _knobRadius * 1.5,
                        padding: 2,
                        borderRadius: BorderRadius.circular(999),
                      ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
