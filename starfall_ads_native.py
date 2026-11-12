
from jnius import autoclass, PythonJavaClass, java_method


PythonActivity = autoclass('org.kivy.android.PythonActivity')


class RewardCallback(PythonJavaClass):
    __javainterfaces__ = ['org/starfall/starfall/RewardCallback']
    __javacontext__ = 'app'

    def __init__(self, callback):
        super().__init__()
        self.callback = callback

    @java_method('(Z)V')
    def onRewarded(self, earned):
        if self.callback:
            self.callback(bool(earned))


def show_rewarded_ad(placement, callback):
    try:
        activity = PythonActivity.mActivity

        if activity is None:
            raise RuntimeError("Android activity is unavailable")

        bridge = autoclass('org.starfall.starfall.StarfallAdsBridge')
        java_callback = RewardCallback(callback)

        bridge.showRewardedAd(
            activity,
            str(placement),
            java_callback
        )

        return True

    except Exception as error:
        print("AdMob error:", repr(error))

        if callback:
            callback(False)

        return False
