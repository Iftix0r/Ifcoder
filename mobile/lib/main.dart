import 'package:firebase_core/firebase_core.dart';
import 'package:flutter/material.dart';

import 'app.dart';
import 'services/location_service.dart';
import 'services/push_service.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();

  // google-services.json fayli bo'lmasa (Firebase hali sozlanmagan bo'lsa),
  // ilova baribir to'liq ishlaydi — faqat push/SMS oqimi ishga tushmaydi.
  try {
    await Firebase.initializeApp();
    await PushService.initialize();
  } catch (_) {
    // Firebase ulanmagan — jim o'tkaziladi.
  }

  await LocationService.initialize();

  runApp(const IfcoderOperatorApp());
}
