import 'package:flutter/material.dart';

/// A square feature tile used in the device detail dashboard grid.
/// Renders a decorative map-like texture background, a circular icon badge,
/// and a rounded label pill at the bottom.
class DashboardTile extends StatelessWidget {
  final IconData icon;
  final String label;
  final String? subtitle;
  final VoidCallback? onPressed;
  final bool alert;

  const DashboardTile({
    super.key,
    required this.icon,
    required this.label,
    this.subtitle,
    required this.onPressed,
    this.alert = false,
  });

  @override
  Widget build(BuildContext context) {
    final iconBgColor = alert
        ? const Color(0xFFF4D4D4)
        : const Color(0xFFB8E6D5);
    final iconColor = alert
        ? const Color(0xFFC43D3D)
        : const Color(0xFF176B5B);
    final labelBgColor = alert
        ? const Color(0xFFC43D3D)
        : const Color(0xFF176B5B);
    final bool interactive = onPressed != null;

    return Material(
      color: Colors.transparent,
      child: InkWell(
        borderRadius: BorderRadius.circular(20),
        onTap: onPressed,
        child: Opacity(
          opacity: !interactive && subtitle == null ? 0.5 : 1,
          child: Container(
            height: 132,
            clipBehavior: Clip.antiAlias,
            decoration: BoxDecoration(
              color: const Color(0xFFEFF3F1),
              borderRadius: BorderRadius.circular(20),
              border: Border.all(color: const Color(0xFFE1E7E4)),
            ),
            child: Stack(
              children: [
                Positioned.fill(
                  child: Image.asset(
                    'assets/images/map_texture_bg.png',
                    fit: BoxFit.cover,
                  ),
                ),
                Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Container(
                      width: 50,
                      height: 50,
                      decoration: BoxDecoration(
                        color: iconBgColor,
                        shape: BoxShape.circle,
                      ),
                      child: Icon(icon, color: iconColor, size: 26),
                    ),
                    if (subtitle != null) ...[
                      const SizedBox(height: 4),
                      Text(
                        subtitle!,
                        textAlign: TextAlign.center,
                        style: const TextStyle(
                          color: Color(0xFF176B5B),
                          fontSize: 11,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                    ],
                    const SizedBox(height: 8),
                    Container(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 16,
                        vertical: 6,
                      ),
                      decoration: BoxDecoration(
                        color: labelBgColor,
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

