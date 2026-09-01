import 'dart:math' as math;

import 'package:flutter/material.dart';

import 'wheelchair_icon.dart';

/// A circular arc gauge showing current speed, with a wheelchair icon in the
/// center and a moving/stopped status label underneath.
class SpeedGauge extends StatelessWidget {
  final double speedKmh;
  final double maxSpeed;
  final bool moving;
  final double size;

  const SpeedGauge({
    super.key,
    required this.speedKmh,
    required this.moving,
    this.maxSpeed = 20,
    this.size = 190,
  });

  @override
  Widget build(BuildContext context) {
    final progress = (speedKmh / maxSpeed).clamp(0.0, 1.0);
    return SizedBox(
      width: size,
      height: size,
      child: Stack(
        alignment: Alignment.center,
        children: [
          CustomPaint(
            size: Size(size, size),
            painter: _GaugePainter(progress: progress),
          ),
          Container(
            width: size * 0.58,
            height: size * 0.58,
            decoration: const BoxDecoration(
              color: Colors.white,
              shape: BoxShape.circle,
            ),
            alignment: Alignment.center,
            child: WheelchairIcon(
              size: size * 0.42,
              padding: 2,
              borderRadius: const BorderRadius.all(Radius.circular(999)),
            ),
          ),
          Positioned(
            bottom: size * 0.06,
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(
                  moving ? '运动' : '停止',
                  style: TextStyle(
                    color: Colors.white.withValues(alpha: 0.95),
                    fontSize: size * 0.075,
                    fontWeight: FontWeight.w600,
                  ),
                ),
                Text(
                  'km/h',
                  style: TextStyle(
                    color: Colors.white.withValues(alpha: 0.85),
                    fontSize: size * 0.065,
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

class _GaugePainter extends CustomPainter {
  final double progress;

  _GaugePainter({required this.progress});

  // Arc spans 270 degrees, starting at 135deg (bottom-left) going clockwise.
  static const double _startAngle = 135 * math.pi / 180;
  static const double _sweepAngle = 270 * math.pi / 180;

  @override
  void paint(Canvas canvas, Size size) {
    final center = Offset(size.width / 2, size.height / 2);
    final radius = size.width / 2 - 10;

    final trackPaint = Paint()
      ..color = Colors.white.withValues(alpha: 0.25)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 8
      ..strokeCap = StrokeCap.round;
    canvas.drawArc(
      Rect.fromCircle(center: center, radius: radius),
      _startAngle,
      _sweepAngle,
      false,
      trackPaint,
    );

    final progressSweep = _sweepAngle * progress;
    if (progressSweep > 0) {
      final progressPaint = Paint()
        ..shader = const SweepGradient(
          startAngle: _startAngle,
          endAngle: _startAngle + _sweepAngle,
          colors: [Color(0xFFBFE3FF), Color(0xFF2E6FF2)],
          transform: GradientRotation(_startAngle),
        ).createShader(Rect.fromCircle(center: center, radius: radius))
        ..style = PaintingStyle.stroke
        ..strokeWidth = 8
        ..strokeCap = StrokeCap.round;
      canvas.drawArc(
        Rect.fromCircle(center: center, radius: radius),
        _startAngle,
        progressSweep,
        false,
        progressPaint,
      );
    }

    _drawEndDot(canvas, center, radius, _startAngle, const Color(0xFFBFE3FF));
    _drawEndDot(
      canvas,
      center,
      radius,
      _startAngle + _sweepAngle,
      const Color(0xFF2E6FF2),
    );
  }

  void _drawEndDot(
    Canvas canvas,
    Offset center,
    double radius,
    double angle,
    Color color,
  ) {
    final dotCenter = Offset(
      center.dx + radius * math.cos(angle),
      center.dy + radius * math.sin(angle),
    );
    canvas.drawCircle(
      dotCenter,
      6,
      Paint()..color = Colors.white,
    );
    canvas.drawCircle(
      dotCenter,
      4,
      Paint()..color = color,
    );
  }

  @override
  bool shouldRepaint(covariant _GaugePainter oldDelegate) {
    return oldDelegate.progress != progress;
  }
}
