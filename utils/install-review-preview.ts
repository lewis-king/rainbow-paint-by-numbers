import { Alert, DevSettings, Platform } from 'react-native';
import * as StoreReview from 'expo-store-review';

let installed = false;

/** Development menu only; never changes saved completion counts or review cadence. */
export function installReviewPreview() {
  if (!__DEV__ || Platform.OS === 'web' || installed) return;
  installed = true;
  DevSettings.addMenuItem('Preview native review dialog', () => {
    void (async () => {
      try {
        if (!await StoreReview.isAvailableAsync()) {
          Alert.alert('Review preview unavailable', 'The native review service is unavailable on this device.');
          return;
        }
        console.info('[Review preview] Requesting the native store dialog. The store controls whether it appears.');
        await StoreReview.requestReview();
        console.info('[Review preview] Native request returned. This does not confirm display or submission.');
      } catch (error) {
        console.warn('[Review preview] Native request failed:', error);
        Alert.alert('Review preview unavailable', 'Try an iOS development build or a Google Play internal test installation.');
      }
    })();
  });
}
