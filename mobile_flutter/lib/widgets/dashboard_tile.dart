import 'package:flutter/material.dart';

/// A square feature tile used in the device detail dashboard grid.
/// Renders a decorative map-like texture background, a circular icon badge,
/// and a rounded label pill at the bottom.
class DashboardTile extends StatelessWidget {
  final IconData icon;
  final String label;
  final VoidCallback? onPressed;
  final bool alert;

  const DashboardTile({
    super.key,
    required this.icon,
    required this.label,
    required this.onPressed,
    this.alert = false,
  });

  @override
  Widget build(BuildContext context) {
    final badgeColor =
        alert ? const Color(0xFFC43D3D) : const Color(0xFF176B5B);
    return Material(
      color: Colors.transparent,
      child: InkWell(
        borderRadius: BorderRadius.circular(16),
        onTap: onPressed,
        child: Opacity(
          opacity: onPressed == null ? 0.5 : 1,
          child: Container(
            height: 132,
            clipBehavior: Clip.antiAlias,
            decoration: BoxDecoration(
              color: const Color(0xFFEFF3F1),
              borderRadius: BorderRadius.circular(16),
              border: Border.all(color: const Color(0xFFE1E7E4)),
            ),
            child: Stack(
              children: [
                Positioned.fill(
                  child: CustomPaint(painter: _MapTexturePainter()),
                ),
                Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Container(
                      width: 46,
                      height: 46,
                      decoration: BoxDecoration(
                        color: badgeColor,
                        shape: BoxShape.circle,
                        boxShadow: [
                          BoxShadow(
                            color: badgeColor.withValues(alpha: 0.35),
                            blurRadius: 8,
                            offset: const Offset(0, 3),
                          ),
                        ],
                      ),
                      child: Icon(icon, color: Colors.white, size: 24),
                    ),
                    const SizedBox(height: 10),
                    Container(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 14,
                        vertical: 5,
                      ),
                      decoration: BoxDecoration(
                        color: badgeColor,
                        borderRadius: BorderRadius.circular(999),
                      ),
                      child: Text(
                        label,
                        style: const TextStyle(
                          color: Colors.white,
                          fontSize: 13,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

/// Purely decorative grid of faint "streets" to evoke a map thumbnail,
/// without pulling in real tile data.
class _MapTexturePainter extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    final linePaint = Paint()
      ..color = const Color(0xFFDCE5E1)
      ..strokeWidth = 1.4;

    const step = 26.0;
    for (double x = -size.height; x < size.width + size.height; x += step) {
      canvas.drawLine(
        Offset(x, 0),
        Offset(x + size.height, size.height),
        linePaint,
      );
    }

    final blobPaint = Paint()..color = const Color(0xFFD8E9F2);
    canvas.drawRRect(
      RRect.fromRectAndRadius(
        Rect.fromLTWH(-14, size.height * 0.55, size.width * 0.55, 26),
        const Radius.circular(10),
      ),
      blobPaint,
    );
  }

  @override
  bool shouldRepaint(covariant _MapTexturePainter oldDelegate) => false;
}
