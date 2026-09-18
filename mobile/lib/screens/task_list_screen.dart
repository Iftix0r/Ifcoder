import 'package:flutter/material.dart';

import '../data/api_client.dart';
import '../data/models/task.dart';
import '../data/token_store.dart';
import '../services/location_service.dart';
import '../services/permissions_service.dart';
import '../services/push_service.dart';
import '../widgets/task_tile.dart';
import 'login_screen.dart';
import 'task_detail_screen.dart';

class TaskListScreen extends StatefulWidget {
  const TaskListScreen({super.key});

  @override
  State<TaskListScreen> createState() => _TaskListScreenState();
}

class _TaskListScreenState extends State<TaskListScreen> with WidgetsBindingObserver {
  final _permissions = PermissionsService();

  List<TaskDto> _tasks = [];
  bool _loading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    PushService.openTaskListRequested.addListener(_onPushOpened);
    _loadTasks();
    _refreshLocationServiceState();
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    PushService.openTaskListRequested.removeListener(_onPushOpened);
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.resumed) {
      _loadTasks();
      _refreshLocationServiceState();
    }
  }

  void _onPushOpened() {
    if (PushService.openTaskListRequested.value) {
      PushService.openTaskListRequested.value = false;
      _loadTasks();
    }
  }

  Future<void> _refreshLocationServiceState() async {
    if (await _permissions.hasForegroundLocation()) {
      await LocationService.start();
    }
  }

  Future<void> _loadTasks() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final tasks = await ApiClient.instance.getTasks();
      if (!mounted) return;
      setState(() => _tasks = tasks);
    } catch (_) {
      if (!mounted) return;
      setState(() => _error = 'Serverga ulanib bo\'lmadi. Internetni tekshiring.');
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _markDone(TaskDto task) async {
    try {
      await ApiClient.instance.updateTaskStatus(task.id, 'done');
      _loadTasks();
    } catch (_) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Holatni o\'zgartirib bo\'lmadi')),
      );
    }
  }

  Future<void> _refreshPermissions() async {
    if (!await _permissions.hasForegroundLocation()) {
      final granted = await _permissions.requestForegroundLocation();
      if (!granted) {
        _showDeniedHint();
        return;
      }
    }
    if (!await _permissions.hasBackgroundLocation()) {
      await _permissions.requestBackgroundLocation();
    }
    if (!await _permissions.isIgnoringBatteryOptimizations()) {
      await _permissions.requestIgnoreBatteryOptimizations();
    }
    await LocationService.start();
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(const SnackBar(
      content: Text(
        'Barcha ruxsatlar berilgan va xizmat qayta ishga tushirildi. Joylashuv baribir '
        'kelmasa: Sozlamalar → Ilovalar → Ifcoder Operator → Batareya bo\'limidan '
        '"Cheklanmagan" tanlang.',
      ),
      duration: Duration(seconds: 6),
    ));
  }

  void _showDeniedHint() {
    ScaffoldMessenger.of(context).showSnackBar(const SnackBar(
      content: Text(
        'Joylashuv ruxsati berilmadi. Sozlamalar → Ilovalar → Ifcoder Operator → '
        'Ruxsatlar → Joylashuv bo\'limidan qo\'lda yoqing.',
      ),
      duration: Duration(seconds: 6),
    ));
  }

  Future<void> _logout() async {
    await LocationService.stop();
    await TokenStore.instance.clear();
    if (!mounted) return;
    Navigator.of(context).pushAndRemoveUntil(
      MaterialPageRoute(builder: (_) => const LoginScreen()),
      (route) => false,
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Vazifalarim'),
        actions: [
          IconButton(
            icon: const Icon(Icons.sync_problem_outlined),
            tooltip: 'Ruxsatlarni yangilash',
            onPressed: _refreshPermissions,
          ),
          IconButton(
            icon: const Icon(Icons.logout),
            tooltip: 'Chiqish',
            onPressed: _logout,
          ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: _loadTasks,
        child: _buildBody(),
      ),
    );
  }

  Widget _buildBody() {
    if (_loading && _tasks.isEmpty) {
      return const Center(child: CircularProgressIndicator());
    }
    if (_error != null && _tasks.isEmpty) {
      return ListView(
        children: [
          const SizedBox(height: 120),
          Icon(Icons.wifi_off, size: 48, color: Theme.of(context).colorScheme.outline),
          const SizedBox(height: 12),
          Center(child: Text(_error!)),
        ],
      );
    }
    if (_tasks.isEmpty) {
      return ListView(
        children: const [
          SizedBox(height: 120),
          Center(child: Text('Sizga tayinlangan vazifalar yo\'q')),
        ],
      );
    }
    return ListView.builder(
      padding: const EdgeInsets.symmetric(vertical: 8),
      itemCount: _tasks.length,
      itemBuilder: (context, index) {
        final task = _tasks[index];
        return TaskTile(
          task: task,
          onTap: () async {
            await Navigator.of(context).push(
              MaterialPageRoute(builder: (_) => TaskDetailScreen(task: task)),
            );
            _loadTasks();
          },
          onMarkDone: () => _markDone(task),
        );
      },
    );
  }
}
