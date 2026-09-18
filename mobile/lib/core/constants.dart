/// Django backend (mobileapi) manzili.
const String kBaseUrl = 'https://iftix0r.uz/api/';

const String kNotificationChannelOps = 'ops_background';
const String kNotificationChannelTasks = 'task_alerts';

/// Joylashuv ping'lari orasidagi interval — native ilovadagi bilan bir xil (3 daqiqa).
const int kLocationUpdateIntervalSeconds = 180;

/// Bitta joylashuv ping'i uchun minimal masofa filtri (metr).
const int kLocationDistanceFilterMeters = 30;

/// Offline navbatda saqlanadigan eng ko'p joylashuv soni.
const int kLocationQueueMaxSize = 20;
