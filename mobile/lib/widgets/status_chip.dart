import 'package:flutter/material.dart';

class StatusChip extends StatelessWidget {
  final String status;
  final String label;

  const StatusChip({super.key, required this.status, required this.label});

  Color _color(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    switch (status) {
      case 'done':
        return Colors.green;
      case 'in_progress':
        return scheme.primary;
      default:
        return scheme.outline;
    }
  }

  @override
  Widget build(BuildContext context) {
    final color = _color(context);
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(20),
      ),
      child: Text(
        label,
        style: TextStyle(color: color, fontWeight: FontWeight.w700, fontSize: 12.5),
      ),
    );
  }
}
