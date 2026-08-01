---
name: spendly-ui-designer
description: Designs and generates modern, production-ready UI for Spendly, a personal expense tracker built on Flask + Jinja2 + vanilla CSS (repo - https://github.com/huzxifakhan123-hub/spendly). Produces clean fintech-style pages and components - cards, forms, tables, dashboards, modals - with consistent spacing, soft shadows, and rounded corners. Use this skill whenever the user asks to design, build, create, redesign, improve, or style any Spendly page, screen, section, or component - including phrasings like "design the X page", "create UI for X", "build a component for X", "make the X look better", "redesign X", or any request about Spendly's frontend, layout, CSS, or visual polish - even when Spendly isn't named explicitly if the conversation context is clearly about it.
disable-model-invocation: true
---

# Spendly UI Designer

You are designing frontend UI for **Spendly**, a personal expense tracker. Spendly is a Flask app with server-rendered Jinja2 templates, vanilla CSS, and a sprinkle of vanilla JS. The goal of this skill is to help you generate UI that feels like it belongs in a polished, modern fintech product - not generic bootstrap-era output, and not React/Tailwind output that doesn't match the stack.

## What Spendly's stack looks like

- **Backend:** Flask (`app.py`), SQLite or similar (`database/`)
- **Templates:** Jinja2 in `templates/` (e.g. `base.html`, `landing.html`, `login.html`, `register.html`, `profile.html`)
- **Styles:** vanilla CSS in `static/css/style.css` - a single stylesheet, no Tailwind, no CSS-in-JS, no preprocessors assumed
- **Scripts:** small amounts of vanilla JS in `static/js/main.js` for interactions (toggles, modals, chart init)
- **Icons:** no icon library - the brand mark is a plain unicode glyph (`◈`); don't introduce Lucide or any other icon CDN

Generate output that fits this stack. Do not introduce React, Vue, Tailwind, shadcn, Bootstrap, or styled-components unless the user explicitly asks for a migration.

## Before you design: check what already exists

If the user's project files are available (e.g. they've shared the repo, uploaded files, or you're inside the codebase), open `base.html`, the main CSS file, and one or two existing templates before generating anything new. The goal is *consistency* - Spendly should feel like one coherent product, not a collage.

Specifically, look for and reuse:

- **Color tokens** (CSS custom properties like `--color-primary`, `--color-bg`, `--color-surface`, etc.)
- **Spacing scale** (if there's a `--space-1`, `--space-2` pattern, use it)
- **Font family and type scale**
- **Existing component classes** - `.card`, `.btn`, `.input`, `.badge`, `.table`, etc.
- **The base layout** - sidebar? topbar? container width? Follow it.

If you can't see the existing files and the request is non-trivial, ask the user to share a screenshot or paste a relevant template before you generate. One screenshot of the existing dashboard saves three rounds of revision.

## The Spendly design language

When you have no existing reference to follow, default to this. It's a clean, fintech-leaning aesthetic - close in spirit to Linear, Notion, or modern banking apps.

**Palette (defaults, override to match existing):** use the CSS custom properties already defined in `static/css/style.css`'s `:root` - don't invent new hex values.
- Background: `--paper` (warm off-white), cards on `--paper-card` (white)
- Text: `--ink` for primary, `--ink-soft` for secondary headings, `--ink-muted` / `--ink-faint` for tertiary text
- Primary accent: `--accent` (dark green), secondary accent `--accent-2` (mustard/orange)
- Semantic: `--danger` for errors/negative amounts; reuse `--accent` / `--accent-2` for positive/category distinctions

**Spacing:** 8px grid. Use multiples of 4px or 8px for padding, gap, margin. Don't use arbitrary values like 13px or 27px.

**Radius:** use `--radius-sm` (6px) for inputs and small elements, `--radius-md` (12px) for cards, `--radius-lg` (20px) for larger surfaces/modals. Pills/badges can be fully rounded (`999px`).

**Shadows:** subtle only. A card shadow like `0 8px 40px rgba(0,0,0,0.06)` (as used on `.mock-card`) is the ceiling. No glows, no heavy drop shadows.

**Typography:** use the fonts already loaded in `base.html` - `var(--font-display)` (`DM Serif Display`) for headings/titles, `var(--font-body)` (`DM Sans`) for body text. Type scale: 12 / 14 / 16 / 20 / 24 / 32. Font weights: 400 body, 500 medium, 600 semibold for headings. Numbers (amounts) should use tabular figures: `font-variant-numeric: tabular-nums`.

**Layout patterns:**
- Card-based composition - group related info in surfaces, don't sprawl
- Generous whitespace - tight layouts read as cluttered in finance apps
- Left-aligned content with clear hierarchy; centered layouts only for empty states and auth
- Tables: zebra stripes optional, but always have row hover, right-align numeric columns
- Forms: label above input, helper text below, error state in red with icon

## Icons

Spendly doesn't use an icon library - the only icon in the project is the plain unicode brand glyph `◈` (`.brand-icon`). Don't introduce Lucide or any other icon CDN. If a design genuinely needs a small visual marker, prefer a unicode glyph, a CSS shape, or an inline SVG with no external dependency, and use it sparingly.

## Output structure

When fulfilling a design request, structure your response like this:

### 1. Short UI plan (2-5 bullets)
Name the key sections of the page/component and any notable UX decisions. Keep it tight - this is orientation, not a spec document. Example: "Dashboard has 4 summary cards on top (balance, income, expenses, savings), a 'recent transactions' table, and a category breakdown donut. Summary cards show trend vs last month as a small delta pill."

### 2. The code
- **Template file(s)** - full Jinja2 with `{% extends "base.html" %}` and a `{% block content %}` unless building `base.html` itself. Use Jinja control flow (`{% for %}`, `{% if %}`) with sensible placeholder variable names the user can wire to their Flask route.
- **CSS** - additions to the existing `static/css/style.css` (Spendly keeps everything in one stylesheet). Scope with a page/component class prefix (`.dashboard-...`, `.tx-table-...`) so styles don't leak.
- **JS** (only if needed) - vanilla, no frameworks. Small and readable.

Put each file in its own fenced code block with a clear header comment or path annotation like `{# templates/dashboard.html #}` or `/* static/css/dashboard.css */`.

### 3. Integration note (1-3 lines)
How to wire it up - which Flask route renders it, what variables the template expects, any new dependency (almost always none). If the user needs to add a link in the sidebar or a route in `app.py`, call that out.

## What to avoid

- **Generic/dated looks** - no `<h1>Welcome to My App</h1>` with default browser styles, no sharp-cornered bordered boxes, no 2012-era bootstrap cards.
- **Code dumps without structure** - always separate template, CSS, and JS into labeled blocks.
- **Over-styling** - if something can be solid color instead of a gradient, use solid. If it can be a border instead of a shadow, use border. Restraint reads as quality.
- **Inconsistent spacing** - if you used 16px for card padding in one place, use 16px in the next place too. No 14px here, 18px there.
- **Random color accents** - one primary accent, semantic colors for meaning, everything else neutral.
- **Clever-but-unclear UX** - a clearly-labeled button beats a mystery icon. In finance, trust matters more than cuteness.
- **Mobile afterthought** - use CSS that works at narrow widths. At minimum, stack cards vertically and make tables horizontally scrollable below ~768px.

## Handling ambiguity

If the user asks for something under-specified ("design the reports page"), make reasonable assumptions and *state them up front* in the UI plan - one line each, no long preamble. For example: "Assuming reports page shows: monthly spend trend, top categories, and a downloadable CSV. Let me know if you want different widgets."

Don't pepper the user with clarifying questions for things you can reasonably decide. Do ask when the answer genuinely changes the output - e.g. "Is this a standalone page or a modal on top of the dashboard?"

## A worked example of the right vibe

**Request:** "Design the add expense form"

**UI plan:**
- Modal dialog (not a full page) - users add expenses inline from the dashboard
- Fields: amount (large, prominent), category (pill selector), date (defaults to today), note (optional)
- Primary action "Add expense" anchors bottom-right; cancel is a subtle text button
- Amount field gets a currency symbol prefix and tabular-nums

**Template:** `templates/partials/add_expense_modal.html` - extends nothing, included via `{% include %}`. Uses a `.modal` overlay pattern already in `style.css` if present.

**CSS:** additions to `static/css/style.css` for the new pill selector; reuses existing `.form-input`, `.btn-primary` classes.

**JS:** small module-free script to open/close the modal and reset the form on close.

That's the shape - concrete, consistent with the stack, visually restrained, and immediately usable.