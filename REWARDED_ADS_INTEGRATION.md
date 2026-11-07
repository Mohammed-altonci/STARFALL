# Rewarded ads bridge contract

The Pygame UI calls an Android-side module named `starfall_ads_native`.

Required API:

```python
show_rewarded_ad(placement, callback) -> bool
```

- Return `True` only when an ad request was accepted and the ad flow started.
- Return `False` if the SDK is unavailable or no ad can be shown.
- Call `callback(True)` only after the user has watched the rewarded ad to completion and the SDK confirms the reward.
- Call `callback(False)` if the ad is closed early, fails to load, or fails to show.
- Callback may run on a native thread; the game callback posts a Pygame event so game-state changes happen in the main loop.
- Supported placements: `continue_after_defeat` and `double_level_coins`.

The Android SDK integration is intentionally not faked in Python. Add Google Mobile Ads SDK and test ad unit IDs through a proper python-for-android/Java bridge before enabling production ads.
