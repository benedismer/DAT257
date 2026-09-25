# Design Steering Document

**Purpose:** This document tells an LLM (or a human) how to make UX and visual design decisions for this website. When in doubt, come back to this file rather than improvising from scratch.

**One-line brief:** Claude.ai's layout discipline and typographic calm, recolored green, with a few deliberate handmade imperfections so it doesn't read as generic AI-generated output.

---

## 1. Reference point: what to borrow from Claude.ai

Take these structural qualities, not the literal brand:

- Generous whitespace, calm information density — content isn't crammed
- Warm off-white background (not stark `#FFFFFF`), warm dark-gray text (not pure black)
- Rounded corners on cards/inputs, but moderate (not pill-shaped everything)
- Soft, subtle shadows — never glossy, gradient-heavy, or "3D button" style
- One accent color used sparingly for interactive elements, not splashed everywhere
- Clean sans-serif for UI, comfortable line-height for reading
- Restrained motion: fades and gentle transitions, no bouncy/flashy animation

## 2. Color system — green instead of orange

Replace every orange accent 1:1 with a green equivalent. Suggested palette:

| Role | Color | Notes |
|---|---|---|
| Primary accent | `#3D6B4F` (muted forest green) | Buttons, links, focus states |
| Accent hover | `#2E5540` | Darker, not brighter |
| Accent light (backgrounds/tags) | `#E4EDE6` | Subtle tint, not neon |
| Background | `#FAF8F3` | Warm off-white, slightly paper-like |
| Text primary | `#2B2A26` | Warm near-black |
| Text secondary | `#6B6A63` | Muted gray-brown |
| Border | `#D9D5C9` | Warm gray, not cold blue-gray |

**Rule:** avoid bright/saturated "kelly green" or neon green — it reads as either Christmas-y or slot-machine-y. Stay muted, mossy, ink-like. Think forest, sage, olive — not lime.

## 3. The "homemade / oldschool" layer — apply lightly

This is the point of departure from Claude.ai, and it should stay a seasoning, not the whole dish. Pick 2–4 of these per page, not all at once:

- A visible 1px border instead of (or in addition to) a soft shadow on some cards — gives a slightly "drawn" feel
- Occasional monospace or typewriter-style font for small labels, timestamps, or metadata (not body text)
- A subtle dotted or dashed divider line instead of a solid one, here and there
- Slightly asymmetric or hand-set spacing on one or two elements (e.g. a heading nudged, an underline that's hand-drawn-looking SVG rather than a perfect CSS border)
- A small textured/paper background on the body (very subtle noise, barely visible) instead of a flat fill
- Buttons with a slightly heavier, hand-drawn-feeling border-radius (e.g. 3–4px, not 12px) instead of the fully smoothed modern pill/rounded-rect

Note: the title bar deliberately carries **no logo or icon mark** — the wordmark
("Rubby") stands on its own. Don't reintroduce a sketched pin/logo in the title.

**What NOT to do:** no Comic Sans, no `<marquee>`/blink, no tiled GIF backgrounds, no rainbow gradients, no "under construction" clip art, no visitor counters. The goal is "made by a person with taste, a little unpolished," not "1998 GeoCities parody." If a choice would make the site look like a joke rather than a personal site, drop it.

## 4. Typography

- **Primary font: monospace / typewriter** (e.g. `"SFMono-Regular", ui-monospace, "Menlo", "Consolas", monospace`) used across the whole UI — headings, body, labels, and metadata. This leans fully into the oldschool early-web feel and is the site's defining typographic choice.
- Keep a single font family for everything; do not mix in a separate sans-serif or serif for body/headings.
- Line length: cap body text around 65–75 characters for readability
- Because monospace is wider and heavier than a proportional font, be a little more generous with spacing and don't set long paragraphs at small sizes.

## 5. Page structure & navigation

Every page follows the same skeleton, top to bottom:

1. **Title bar** — full-width strip at the very top of the page, holding the site title **"Rubby"**. The title is **center-aligned** and set roughly **twice the size** of the nav/body text so it reads as the clear page header. No logo or icon accompanies it — the wordmark stands alone.
2. **Page nav row** — directly beneath the title bar, a simple horizontal row listing every page as a link, side by side (e.g. `Page 1   Page 2   Page 3`). Not a dropdown or hamburger menu — all pages visible at once, **center-aligned** (matching the centered title). Keep it plain text links with the green accent on hover/active state.
3. **Content area** — a single main content block below the nav row, taking up most of the page.

Known pages and their content areas:

- **Home page:** content area is a map. The map shows a pin/marker for an event's location; clicking or hovering the pin can surface the event details (e.g. "location of event").
- **Events page:** content area is a vertical list of events.

Keep the title bar and nav row visually consistent (same height, same border/background treatment) across every page, so the site feels like one coherent shell with different content dropped into the same frame — this is also a good place to apply the "visible border instead of shadow" homemade touch from Section 3, since it's a structural element rather than decoration.

## 6. Components — quick rules

- **Buttons:** solid green fill for primary actions, outlined/ghost for secondary. Border-radius ~4–8px (less rounded than typical modern SaaS). No gradients, no drop shadows on hover — just a color shift.
- **Links:** green, underline on hover (not always-on unless in body text)
- **Cards:** either soft shadow OR visible border — pick one per section, don't stack both everywhere
- **Forms/inputs:** simple rectangular fields, thin border, green focus ring — avoid overly rounded "pill" inputs
- **Icons:** simple line icons, not filled/glossy; a hand-drawn/sketch icon set is a good place to lean into the homemade feel if used consistently

## 7. Motion

- Transitions under 200ms, ease-out
- No bounce, no spin, no parallax gimmicks
- It's fine — even nice — if a hover state feels slightly "clicky" rather than perfectly smooth, in keeping with the handmade feel

## 8. Voice & content tone

- Direct, warm, a little understated — avoid marketing-speak ("Unlock your potential!", "Revolutionize your workflow!")
- Short sentences over long ones
- First person is fine if the site is personal

## 9. Quick checklist for any new UI decision

1. Does this feel calm and uncluttered? (Claude.ai influence)
2. Is green the only accent color doing work here?
3. Have I added at least one small handmade touch on this page, without overdoing it?
4. Would a stranger call this "AI slop"? If yes, add one imperfection or remove one polish effect.
5. Am I still readable and accessible (contrast, font size, spacing)?

---

*Use this as the standing reference for design/UX decisions on this site. Update it directly if the direction evolves rather than re-deriving the rules each time.*