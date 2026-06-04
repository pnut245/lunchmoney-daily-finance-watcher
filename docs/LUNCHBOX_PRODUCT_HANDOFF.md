# Lunchbox Product Handoff

This document is the shortest useful handoff for a new ChatGPT thread to take the lead on product polish.

## What Exists Now

- A working native iPhone app and widget prototype.
- Real Lunch Money data is flowing through the local watcher into the phone experience.
- The Mac hosts a local snapshot endpoint for the phone at `http://<mac-lan-ip>:8422/data/widget_snapshot.json`.
- The finance watcher now refreshes the source snapshot at the top of each hour.
- The phone app can fetch the latest snapshot manually right now.
- The widget is technically working, but the product behavior and presentation still feel developer-oriented.

## Active Code Surface

These are the files that matter most for product cleanup:

- `ios/Lunchbox/ContentView.swift`
- `ios/Lunchbox/AppViewModel.swift`
- `ios/OneNumberWidget/LunchboxWidget.swift`
- `ios/OneNumberWidget/LunchboxWidgetIntent.swift`
- `ios/Shared/LunchboxSnapshot.swift`
- `ios/Shared/SnapshotFetcher.swift`
- `ios/Shared/SnapshotStore.swift`
- `docs/PRODUCT.md`
- `docs/DESIGN.md`
- `docs/V1_IMPLEMENTATION.md`

## Current Product Problem

The prototype works, but it does not yet feel like the intended product.

Right now it is still too much of a developer control panel:

- too much setup/config UI on the main screen
- too much visible implementation detail
- too much emphasis on fetching and URLs
- not enough emphasis on the one-number emotional experience
- stale, loading, and error states are still functional rather than elegant

The infrastructure is no longer the main problem. Product shape is.

## Product Intent

The core idea is:

> one calm number that answers “can I spend today?”

Desired feel:

- quiet
- legible in one glance
- low shame
- low cognitive load
- intentional rather than dashboard-like

The number should dominate. Everything else should justify its existence.

## Important Constraints

- The Mac-side watcher is read-only with Lunch Money.
- The source snapshot can refresh exactly on the hour on the Mac.
- iPhone widget refresh timing is approximate because Apple controls widget budgets.
- The phone app and widget are reading a local-network snapshot, not calling Lunch Money directly.
- The current setup assumes the phone and Mac are on the same local network.
- The background server is a user `LaunchAgent`, so it depends on the Mac being awake and logged in.

## What Is Already Decided

- The app/project name is `Lunchbox`.
- The widget target is `OneNumberWidget`.
- The app is for real personal finance data, not mocked demo data.
- The system should feel “live-ish,” with hourly source updates.
- The main value is the daily number, not analytics.
- The current architecture should be preserved unless there is a strong reason to change it.

## What Should Be Improved Next

### 1. Main app experience

The app should stop feeling like a transport/config screen and start feeling like a real product.

Likely direction:

- make the one number the obvious primary surface
- demote or hide raw URL editing from the main experience
- move setup into a secondary area
- clarify success, stale, and error states in human language

### 2. Widget behavior and hierarchy

The widget should feel like the true product surface.

Likely direction:

- reduce visible chrome
- emphasize only the essential number and its meaning
- avoid dev-looking placeholder or loading states
- decide exactly how much secondary context belongs in the widget

### 3. States, not just happy path

The product needs intentional handling for:

- fresh data
- stale but usable data
- no network to Mac
- snapshot fetch failed
- no data yet
- negative number / overspend state

### 4. Visual language

The conceptual docs already point in a stricter direction than the current build.

Open design tension to resolve:

- concept docs say “the number is the interface”
- current app still includes cards, controls, and multiple support metrics

ChatGPT should decide whether:

- V1 app should also be radically minimal, or
- the widget should be ultra-minimal while the app can remain a calmer settings-plus-context surface

## Screens To Review

Useful recent screenshots:

- the two June 3 screenshots on the Desktop from roughly `5:13 PM`

They show:

- the widget on the phone home screen
- the in-app snapshot source and fetch screen
- the current mismatch between infrastructure maturity and product maturity

## Recommended ChatGPT Role

ChatGPT should lead as a product/design partner first, then propose implementation changes second.

Best stance:

- preserve working infra
- simplify the user experience aggressively
- keep the one-number premise sacred
- make the app feel intentional, not experimental

## Paste-Ready Prompt

Use this in a new ChatGPT thread:

```text
I want you to take the lead on product polish for my iPhone prototype called Lunchbox.

Please use this repo handoff doc as the source of truth:
/Users/patrickfoley/Documents/Playground/lunchmoney-daily-finance-watcher/docs/LUNCHBOX_PRODUCT_HANDOFF.md

Important context:
- the native prototype is already working on a real iPhone
- real Lunch Money data is feeding it through a local Mac-hosted snapshot
- the Mac refreshes the source snapshot hourly at the top of the hour
- the infrastructure is mostly solved
- the product experience is not solved yet

I want you to lead on:
- product shape
- widget-first thinking
- better state handling
- simplification of the app UX
- deciding what belongs in the app versus the widget

I do not want a dashboard.
I want a calm, intentional one-number product.

Please start by reading:
- /Users/patrickfoley/Documents/Playground/lunchmoney-daily-finance-watcher/docs/LUNCHBOX_PRODUCT_HANDOFF.md
- /Users/patrickfoley/Documents/Playground/lunchmoney-daily-finance-watcher/docs/PRODUCT.md
- /Users/patrickfoley/Documents/Playground/lunchmoney-daily-finance-watcher/docs/DESIGN.md
- /Users/patrickfoley/Documents/Playground/lunchmoney-daily-finance-watcher/docs/V1_IMPLEMENTATION.md

Then give me:
1. your read of what the product should be
2. the biggest product problems in the current prototype
3. a recommended V1 app + widget behavior model
4. a concrete implementation plan for the next pass
```
