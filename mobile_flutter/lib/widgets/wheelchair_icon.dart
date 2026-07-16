import 'package:flutter/material.dart';

class WheelchairIcon extends StatelessWidget {
  final double size;
  final double padding;
  final BorderRadius borderRadius;

  const WheelchairIcon({
    super.key,
    required this.size,
    this.padding = 4,
    this.borderRadius = const BorderRadius.all(Radius.circular(8)),
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      width: size,
      height: size,
      padding: EdgeInsets.all(padding),
      clipBehavior: Clip.antiAlias,
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: borderRadius,
      ),
      child: Image.asset(
        'assets/images/wheelchair.png',
        fit: BoxFit.contain,
        cacheWidth: 256,
        filterQuality: FilterQuality.medium,
      ),
    );
  }
}
