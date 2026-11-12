
[app]
p4a.branch = v2024.01.21
android.ndk = 25b
title = Starfall
package.name = starfall
package.domain = org.starfall
source.dir = .
source.include_exts = py
version = 1.0
requirements = python3,pygame-ce,pyjnius
p4a.local_recipes = ./p4a-recipes
orientation = landscape
fullscreen = 1
android.permissions = INTERNET, ACCESS_NETWORK_STATE
android.api = 35
android.minapi = 24
android.archs = arm64-v8a
android.accept_sdk_license = True
android.add_src = ./android_src
android.gradle_dependencies = com.google.android.gms:play-services-ads:25.5.0
android.enable_androidx = True
android.meta_data = com.google.android.gms.ads.APPLICATION_ID=ca-app-pub-3940256099942544~3347511713

[buildozer]
log_level = 2
warn_on_root = 1
