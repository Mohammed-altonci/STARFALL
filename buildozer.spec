[app]
title = Starfall
package.name = starfall
package.domain = org.starfall
source.dir = .
source.include_exts = py
version = 1.0
requirements = python3,pygame-ce
p4a.local_recipes = ./p4a-recipes
orientation = landscape
fullscreen = 1
android.permissions =
android.api = 33
android.minapi = 21
android.archs = arm64-v8a
android.accept_sdk_license = True

[buildozer]
log_level = 2
warn_on_root = 1
