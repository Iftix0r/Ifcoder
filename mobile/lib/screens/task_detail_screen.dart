import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

import '../data/api_client.dart';
import '../data/models/task.dart';
import '../services/permissions_service.dart';
import '../services/sms_service.dart';
import '../widgets/status_chip.dart';

class TaskDetailScreen extends StatefulWidget {
  final TaskDto task;

  const TaskDetailScreen({super.key, required this.task});

  @override
  State<TaskDetailScreen> createState() => _TaskDetailScreenState();
}

class _TaskDetailScreenState extends State<TaskDetailScreen> {
  final _permissions = PermissionsService();
  late TaskDto _task;
  bool _updating = false;

  @override
  void initState() {
    super.initState();
    _task = widget.task;
  }

  String? get _nextStatus => switch (_task.status) {
        'todo' => 'in_progress',
        'in_progress' => 'done',
        _ => null,
      };

  String _statusLabelFor(String status) => switch (status) {
        'todo' => 'Bajarilmagan',
        'in_progress' => 'Jarayonda',
        'done' => 'Bajarilgan',
        _ => status,
      };

  String get _actionLabel => _task.status == 'todo' ? 'Boshlash' : 'Bajarildi';

  Future<void> _advanceStatus() async {
    final next = _nextStatus;
    if (next == null) return;
    setState(() => _updating = true);
    try {
      final ok = await ApiClient.instance.updateTaskStatus(_task.id, next);
      if (ok) {
        setState(() => _task = _task.copyWith(status: next, statusLabel: _statusLabelFor(next)));
      } else if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Holatni o\'zgartirib bo\'lmadi')));
      }
    } catch (_) {
      if (mounted) {
        ScaffoldMessenger.of(context)
            .showSnackBar(const SnackBar(content: Text('Serverga ulanib bo\'lmadi. Internetni tekshiring.')));
      }
    } finally {
      if (mounted) setState(() => _updating = false);
    }
  }

  Future<void> _call() async {
    if (_task.clientPhone.isEmpty) {
      _showSnack('Mijozning telefon raqami kiritilmagan');
      return;
    }
    final uri = Uri(scheme: 'tel', path: _task.clientPhone);
    await launchUrl(uri);
  }

  Future<void> _promptSms() async {
    if (_task.clientPhone.isEmpty) {
      _showSnack('Mijozning telefon raqami kiritilmagan');
      return;
    }
    if (!await _permissions.hasSms()) {
      final granted = await _permissions.requestSms();
      if (!granted) return;
    }
    if (!mounted) return;
    final defaultText =
        'Assalomu alaykum, ${_task.clientName}! "${_task.title}" bo\'yicha siz bilan bog\'lanmoqchi edik.';
    final controller = TextEditingController(text: defaultText);
    final sendText = await showDialog<String>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Mijozga SMS'),
        content: TextField(controller: controller, maxLines: 4, autofocus: true),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context), child: const Text('Bekor qilish')),
          FilledButton(
            onPressed: () => Navigator.pop(context, controller.text),
            child: const Text('Yuborish'),
          ),
        ],
      ),
    );
    if (sendText == null || sendText.isEmpty) return;
    final sent = await SmsService().sendSms(_task.clientPhone, sendText);
    _showSnack(sent ? 'SMS yuborildi' : 'SMS yuborilmadi');
  }

  void _showSnack(String message) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(message)));
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Vazifa tafsilotlari')),
      body: ListView(
        padding: const EdgeInsets.all(20),
        children: [
          Text(_task.title, style: Theme.of(context).textTheme.headlineSmall?.copyWith(fontWeight: FontWeight.w800)),
          const SizedBox(height: 12),
          StatusChip(status: _task.status, label: _task.statusLabel),
          const SizedBox(height: 20),
          Text(
            _task.description.isEmpty ? 'Tavsif kiritilmagan' : _task.description,
            style: Theme.of(context).textTheme.bodyMedium,
          ),
          const SizedBox(height: 24),
          _InfoRow(label: 'Mijoz', value: _task.clientName.isEmpty ? 'Mijoz biriktirilmagan' : _task.clientName),
          _InfoRow(label: 'Loyiha', value: _task.projectName.isEmpty ? '—' : _task.projectName),
          _InfoRow(label: 'Muddat', value: _task.dueDate ?? '—'),
          _InfoRow(label: 'Muhimlik', value: _task.priorityLabel),
          const SizedBox(height: 28),
          Row(
            children: [
              Expanded(
                child: OutlinedButton.icon(
                  onPressed: _call,
                  icon: const Icon(Icons.call_outlined),
                  label: const Text('Qo\'ng\'iroq qilish'),
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: OutlinedButton.icon(
                  onPressed: _promptSms,
                  icon: const Icon(Icons.sms_outlined),
                  label: const Text('SMS yuborish'),
                ),
              ),
            ],
          ),
          if (_nextStatus != null) ...[
            const SizedBox(height: 16),
            FilledButton(
              onPressed: _updating ? null : _advanceStatus,
              child: _updating
                  ? const SizedBox(
                      width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                  : Text(_actionLabel),
            ),
          ],
        ],
      ),
    );
  }
}

class _InfoRow extends StatelessWidget {
  final String label;
  final String value;

  const _InfoRow({required this.label, required this.value});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 6),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 90,
            child: Text(label, style: TextStyle(color: Theme.of(context).colorScheme.onSurfaceVariant)),
          ),
          Expanded(child: Text(value, style: const TextStyle(fontWeight: FontWeight.w600))),
        ],
      ),
    );
  }
}
