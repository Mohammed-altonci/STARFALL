
package org.starfall.starfall;

import android.app.Activity;
import com.google.android.gms.ads.AdError;
import com.google.android.gms.ads.AdRequest;
import com.google.android.gms.ads.FullScreenContentCallback;
import com.google.android.gms.ads.LoadAdError;
import com.google.android.gms.ads.MobileAds;
import com.google.android.gms.ads.rewarded.RewardedAd;
import com.google.android.gms.ads.rewarded.RewardedAdLoadCallback;

public class StarfallAdsBridge {

    private static final String TEST_AD_UNIT =
        "ca-app-pub-3940256099942544/5224354917";

    private static RewardedAd rewardedAd;
    private static boolean isLoading = false;
    private static boolean isInitialized = false;

    private static RewardCallback pendingCallback;
    private static Activity pendingActivity;

    public static void showRewardedAd(
            Activity activity,
            String placement,
            RewardCallback callback) {

        activity.runOnUiThread(() -> {
            if (rewardedAd != null) {
                showLoadedAd(activity, callback);
                return;
            }

            pendingCallback = callback;
            pendingActivity = activity;

            if (!isInitialized) {
                isInitialized = true;
                MobileAds.initialize(activity, status -> {
                    loadRewardedAd(activity);
                });
            } else if (!isLoading) {
                loadRewardedAd(activity);
            }
        });
    }

    private static void loadRewardedAd(Activity activity) {
        if (isLoading) return;

        isLoading = true;

        AdRequest request = new AdRequest.Builder().build();

        RewardedAd.load(
            activity,
            TEST_AD_UNIT,
            request,
            new RewardedAdLoadCallback() {

                @Override
                public void onAdLoaded(RewardedAd ad) {
                    isLoading = false;
                    rewardedAd = ad;

                    if (pendingCallback != null &&
                        pendingActivity != null) {

                        showLoadedAd(
                            pendingActivity,
                            pendingCallback
                        );
                    }
                }

                @Override
                public void onAdFailedToLoad(LoadAdError error) {
                    isLoading = false;
                    rewardedAd = null;
                    finishCallback(false);
                }
            }
        );
    }

    private static void showLoadedAd(
            Activity activity,
            RewardCallback callback) {

        RewardedAd ad = rewardedAd;
        rewardedAd = null;

        if (ad == null) {
            if (callback != null) callback.onRewarded(false);
            return;
        }

        final boolean[] earned = {false};

        ad.setFullScreenContentCallback(
            new FullScreenContentCallback() {

                @Override
                public void onAdDismissedFullScreenContent() {
                    callback.onRewarded(earned[0]);
                    loadRewardedAd(activity);
                }

                @Override
                public void onAdFailedToShowFullScreenContent(
                        AdError error) {
                    callback.onRewarded(false);
                    loadRewardedAd(activity);
                }
            }
        );

        ad.show(activity, rewardItem -> {
            earned[0] = true;
        });
        
        pendingCallback = null;
        pendingActivity = null;
    }

    private static void finishCallback(boolean earned) {
        if (pendingCallback != null) {
            pendingCallback.onRewarded(earned);
        }

        pendingCallback = null;
        pendingActivity = null;
    }
}
