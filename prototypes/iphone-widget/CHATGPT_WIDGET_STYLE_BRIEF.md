# Lunchbox Widget Style Brief

Use this file as the style and creative-direction handoff for the `Lunchbox` finance widget prototype in this repo.

## Goal

Design a finance widget that feels useful for an ADHD brain:

- extremely fast to scan
- emotionally legible at a glance
- visually calm but not bland
- high-contrast hierarchy
- focused on action and state, not accounting detail

## Product framing

This is not a traditional budgeting dashboard. It should feel more like a "financial nervous system" or "money weather report" than a spreadsheet.

The widget should answer, within about one second:

- Am I safe or not?
- What matters today?
- Is my current spending state green / yellow / red?
- Do I need to slow down, hold, or can I spend freely?

## Core visual direction

- Make the spending state the dominant element.
- Treat "Today", "Week", and dopamine/fun money as the next-most important numbers.
- Remove non-essential metadata and dense secondary labels.
- Prefer bold, simple composition over clever detail.
- Use strong status language and unmistakable color/state cues.
- Avoid a finance-app look that feels corporate, sterile, or overloaded.

## Tone

- clear
- kind
- slightly urgent when needed
- never shamey
- never noisy
- more "coach" than "ledger"

## What to avoid

- tiny labels
- crowded cards
- multiple competing accent colors
- heavy tables
- account-level detail
- merchant-level detail
- over-explaining the math
- generic fintech polish that hides the actual state

## Existing prototype assets

Primary prototype folder:

- `/Users/patrickfoley/Documents/Playground/lunchmoney-daily-finance-watcher/prototypes/iphone-widget/`

Best reference images:

- `/Users/patrickfoley/Documents/Playground/lunchmoney-daily-finance-watcher/prototypes/iphone-widget/exports/iphone-widget-prototype-window-clean.png`
- `/Users/patrickfoley/Documents/Playground/lunchmoney-daily-finance-watcher/prototypes/iphone-widget/exports/iphone-widget-prototype-board-clean.png`
- `/Users/patrickfoley/Documents/Playground/lunchmoney-daily-finance-watcher/prototypes/iphone-widget/exports/iphone-widget-prototype-phone-clean.png`

Related implementation files:

- `/Users/patrickfoley/Documents/Playground/lunchmoney-daily-finance-watcher/prototypes/iphone-widget/index.html`
- `/Users/patrickfoley/Documents/Playground/lunchmoney-daily-finance-watcher/prototypes/iphone-widget/styles.css`
- `/Users/patrickfoley/Documents/Playground/lunchmoney-daily-finance-watcher/prototypes/iphone-widget/script.js`
- `/Users/patrickfoley/Documents/Playground/lunchmoney-daily-finance-watcher/prototypes/iphone-widget/swiftui/LunchboxWidget.swift`

## Design prompts for ChatGPT

If you are helping redesign the widget, bias toward:

- fewer elements, larger type
- one dominant state headline
- one to three oversized supporting numbers
- obvious status bands or modes
- a layout that still works when the user is stressed, distracted, or impulsive
- small, medium, and lock-screen variants that all preserve the same hierarchy

## Suggested language patterns

Prefer short stateful phrases like:

- Safe today
- Watch it
- Hold spending
- Free to spend
- Tight week
- Fun money OK

Avoid verbose labels like:

- Remaining discretionary allocation this week
- Month-to-date spending velocity
- Category utilization summary

## Notes for next phase

Xcode is now installed, so this brief can be used as creative direction for turning the existing SwiftUI scaffold into a real WidgetKit implementation.
