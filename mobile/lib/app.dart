import 'package:flutter/material.dart';

import 'core/theme.dart';
import 'screens/splash_screen.dart';

class IfcoderOperatorApp extends StatelessWidget {
  const IfcoderOperatorApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Ifcoder Operator',
      debugShowCheckedModeBanner: false,
      theme: buildLightTheme(),
      darkTheme: buildDarkTheme(),
      themeMode: ThemeMode.system,
      home: const SplashScreen(),
    );
  }
}
