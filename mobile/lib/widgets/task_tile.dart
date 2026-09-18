import 'package:flutter/material.dart';

import '../data/models/task.dart';
import 'status_chip.dart';

class TaskTile extends StatelessWidget {
  final TaskDto task;
  final VoidCallback onTap;
  final VoidCallback onMarkDone;

  const TaskTile({super.key, required this.task, required this.onTap, required this.onMarkDone});

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 6),
      child: InkWell(
        borderRadius: BorderRadius.circular(18),
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      task.title,
                      style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w700),
                    ),
                    const SizedBox(height: 6),
                    Text(
                      task.clientName.isEmpty ? 'Mijoz biriktirilmagan' : task.clientName,
                      style: Theme.of(context).textTheme.bodySmall?.copyWith(
                            color: Theme.of(context).colorScheme.onSurfaceVariant,
                          ),
                    ),
                    const SizedBox(height: 10),
                    Row(
                      children: [
                        StatusChip(status: task.status, label: task.statusLabel),
                        const SizedBox(width: 8),
                        if (task.dueDate != null)
                          Text(
                            task.dueDate!,
                            style: Theme.of(context).textTheme.bodySmall,
                          ),
                      ],
                    ),
                  ],
                ),
              ),
              if (task.status != 'done')
                IconButton(
                  icon: const Icon(Icons.check_circle_outline),
                  tooltip: 'Bajarildi',
                  onPressed: onMarkDone,
                ),
            ],
          ),
        ),
      ),
    );
  }
}
