# Preview and verify the review request

## Visual preview now

Open `design/review-flow.html` in a browser. It illustrates the iOS and Android
dialogs over the gallery, with empty stars and an interactive 10 → 20 → 30 cadence.
`review-flow.png` is the corresponding screenshot. These are illustrations,
not proof that a native store dialog appeared. Store appearance varies by OS.

## Native development shortcut

Development builds register **Preview native review dialog** in the React Native
developer menu. Open the menu by shaking a development device, or use Android
`adb shell input keyevent 82`. The shortcut calls the real `expo-store-review`
bridge and leaves painting progress and the persisted review cadence untouched.
It is guarded by `__DEV__` and is unavailable in production builds. It does not
substitute a custom dialog when a store declines to display its own.

### iOS

Use this app's development build on an iPhone or an Xcode simulator. Apple's
development mode displays the native rating sheet; TestFlight deliberately does
not. This Linux workstation cannot run an iOS simulator. Do not treat a
TestFlight no-show as an implementation failure, or an Expo Go dialog as a
review of this app's bundle.

[Apple's documented development/TestFlight behavior](https://developer.apple.com/documentation/storekit/skstorereviewcontroller/requestreview()).

### Android

For an actual card, use Google Play **internal app sharing** or an **internal
test track** before the production release. Internal sharing displays the card
with submission disabled. Internal-track testers need the app in their Play
library, the eligible account selected, and no existing review for the app.
The internal track does not apply the normal prompt quota.

A sideloaded debug APK or emulator is useful for checking the gallery, painting,
video playback and native bridge calls, but a successful API return does not
prove a card displayed. `FakeReviewManager` does not render the card either.
Publishing or uploading a test build is a separate step; none has been uploaded
as part of this local preview.

[Google's native review testing instructions](https://developer.android.com/guide/playcore/in-app-review/test).

## End-to-end cadence check

On a dedicated fresh test installation:

1. Finish nine different pictures and return to the gallery: no request.
2. Finish a tenth; enjoy the reward; return to the gallery: request after one second.
3. Dismiss the store sheet. Reopen/repaint an already-completed picture: no extra count.
4. Complete ten more different pictures: next request at twenty total.
5. Complete another ten: next request at thirty total.
6. Background the app or enter a picture before the delay expires: no dialog over gameplay.

Do not clear progress on a child's installation for this test. The app records
requests, not reviews: neither store tells us whether a rating was submitted.
In production, OS eligibility and quotas may suppress any request.

## Verification evidence so far

- Six cadence/storage/lifecycle tests pass, including delayed hydration and leaving
  the gallery during the native availability check.
- TypeScript checking passes with the development shortcut.
- Browser preview interaction verified: both illustrations appear at ten,
  next threshold becomes twenty, one-star selection works, reset dismisses both.
- Native device execution and an actual displayed store sheet remain to verify.
- Analytics remains deferred and is not part of this release.
