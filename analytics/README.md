# Engagement analytics setup

**Deferred by the owner on 2026-10-04.** The next app update contains new
painting assets and the native review request only. Do not wire or enable
analytics in that update. The setup below is preserved for separate future work;
`analytics/` is excluded from the EAS upload. No Firebase SDK/config plugin is
present in the app dependency/configuration files.

Google Analytics account **154924733**, property **557245199**, remains the
reporting property. Firebase project `rainbow-paint-by-numbers` links the native
apps to it; this is not a replacement Analytics account.

| Platform | Package / bundle ID | Stream ID |
| --- | --- | --- |
| Android | king.meezy.rainbowpaintbynumbers | 16038899973 |
| iOS | king.meezy.rainbowpaintbynumbers | 16038997970 |

`setup.json` records the Firebase Management API's verified association.
`config/` contains native client configuration downloaded for those apps.
These files alone do not enable collection. No Analytics SDK is installed or
collecting events yet.

## Cost constraint

Keep Firebase on Spark. `billing-status.json` records `billingEnabled: false`
and an empty billing account. Do not attach billing, upgrade to Blaze, or add a
paid processing service. [Firebase Analytics is a no-cost product](https://firebase.google.com/pricing).

## Reporting and remaining implementation

`utils/painting-events.ts` defines selections, actual painting starts, progress
milestones, completions, leaving/resuming, resets and reward views. Restoring a
saved picture must not count as a new completion. Foreground painting duration
excludes background and reward-viewing time. These event semantics have tests;
the transport and screen wiring are not yet complete.

This app targets young children. Standard Firebase app-instance identifiers
must not be described as anonymous simply because advertising identifiers are
disabled. [Apple's Kids Category rules](https://developer.apple.com/app-store/review/guidelines/#kids-category)
limit third-party analytics and transmission of identifiable device information.
The proposed reporting approach is first-party anonymous totals per picture,
without child/device/session identifiers. Reporting choices are deferred with
analytics. Do not enable collection until its data flow, provider configuration,
privacy text and platform disclosures have been reviewed and verified.

Native GA Measurement Protocol requires an app instance ID; do not fabricate
one to make aggregate reports appear to be native app user/session analytics.
No real child data has been sent as a setup test.
