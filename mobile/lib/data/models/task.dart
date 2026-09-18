class TaskDto {
  final int id;
  final String title;
  final String description;
  final String status;
  final String statusLabel;
  final String priority;
  final String priorityLabel;
  final String? dueDate;
  final String clientName;
  final String clientPhone;
  final String projectName;

  const TaskDto({
    required this.id,
    required this.title,
    required this.description,
    required this.status,
    required this.statusLabel,
    required this.priority,
    required this.priorityLabel,
    required this.dueDate,
    required this.clientName,
    required this.clientPhone,
    required this.projectName,
  });

  factory TaskDto.fromJson(Map<String, dynamic> json) => TaskDto(
        id: json['id'] as int,
        title: json['title'] as String? ?? '',
        description: json['description'] as String? ?? '',
        status: json['status'] as String? ?? 'todo',
        statusLabel: json['status_label'] as String? ?? '',
        priority: json['priority'] as String? ?? 'medium',
        priorityLabel: json['priority_label'] as String? ?? '',
        dueDate: json['due_date'] as String?,
        clientName: json['client_name'] as String? ?? '',
        clientPhone: json['client_phone'] as String? ?? '',
        projectName: json['project_name'] as String? ?? '',
      );

  TaskDto copyWith({String? status, String? statusLabel}) => TaskDto(
        id: id,
        title: title,
        description: description,
        status: status ?? this.status,
        statusLabel: statusLabel ?? this.statusLabel,
        priority: priority,
        priorityLabel: priorityLabel,
        dueDate: dueDate,
        clientName: clientName,
        clientPhone: clientPhone,
        projectName: projectName,
      );
}
