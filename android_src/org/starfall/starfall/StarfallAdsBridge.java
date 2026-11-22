
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

    private static final String CONTINUE_AD =
        "ca-app-pub-3170795820395582/3092497265";

    private static final String DOUBLE_REWARD_AD =
        "ca-app-pub-3170795820395582/8017200087";

    private static final String CRYSTALS_AD =
        "ca-app-pub-3170795820395582/1615764066";

    private static boolean isInitialized = false;
    private static boolean isLoading = false;

    public static void showRewardedAd(
            Activity activity,
            String placement,
            RewardCallback callback) {

        if (activity == null) {
            notifyResult(callback, false);
            return;
        }

        activity.runOnUiThread(() -> {

            String adUnit = getAdUnit(placement);

            if (adUnit == null || isLoading) {
                notifyResult(callback, false);
                return;
            }

            isLoading = true;

            if (!isInitialized) {

                MobileAds.initialize(activity, status -> {
                    isInitialized = true;
                    loadRewardedAd(activity, adUnit, callback);
                });

            } else {

                loadRewardedAd(activity, adUnit, callback);
            }
        });
    }

    private static String getAdUnit(String placement) {

        if ("continue_after_defeat".equals(placement)) {
            return CONTINUE_AD;
        }

        if ("double_level_coins".equals(placement)) {
            return DOUBLE_REWARD_AD;
        }

        if ("crystal_reward".equals(placement)) {
            return CRYSTALS_AD;
        }

        return null;
    }

    private static void loadRewardedAd(
            Activity activity,
            String adUnit,
            RewardCallback callback) {

        AdRequest request = new AdRequest.Builder().build();

        RewardedAd.load(
            activity,
            adUnit,
            request,
            new RewardedAdLoadCallback() {

                @Override
                public void onAdLoaded(RewardedAd ad) {

                    showLoadedAd(activity, ad, callback);
                }

                @Override
                public void onAdFailedToLoad(LoadAdError error) {

                    isLoading = false;
                    notifyResult(callback, false);
                }
            }
        );
    }

    private static void showLoadedAd(
            Activity activity,
            RewardedAd ad,
            RewardCallback callback) {

        final boolean[] earned = {false};
        final boolean[] completed = {false};

        ad.setFullScreenContentCallback(
            new FullScreenContentCallback() {

                @Override
                public void onAdDismissedFullScreenContent() {

                    if (!completed[0]) {
                        completed[0] = true;
                        isLoading = false;
                        notifyResult(callback, earned[0]);
                    }
                }

                @Override
                public void onAdFailedToShowFullScreenContent(
                        AdError error) {

                    if (!completed[0]) {
                        completed[0] = true;
                        isLoading = false;
                        notifyResult(callback, false);
                    }
                }
            }
        );

        try {

            ad.show(activity, rewardItem -> {
                earned[0] = true;
            });

        } catch (Exception error) {

            if (!completed[0]) {
                completed[0] = true;
                isLoading = false;
                notifyResult(callback, false);
            }
        }
    }

    private static void notifyResult(
            RewardCallback callback,
            boolean earned) {

        if (callback != null) {
            callback.onRewarded(earned);
        }
    }
}
