# Design Token System

## Token Categories

### Base Colors

```css
:root {
  /* Brand */
  --primary: #BFB571;           /* Gold brand color */
  --primary-fg: #222222;        /* Text on primary */
  --accent: #EC6F66;            /* Coral accent */
  --accent-fg: #222222;         /* Text on accent */

  /* Surfaces */
  --bg: #ffffff;                /* Page background */
  --content: #222222;           /* Primary text */
  --surface: #fafafa;           /* Card/panel background */
  --surface-hover: #f3f3f3;     /* Interactive surface hover */
  --border: #e6e6e6;            /* Borders */
  --muted: #737373;             /* Secondary text */

  /* Status */
  --success: #16a34a;
  --warning: #d97706;
  --danger: #dc2626;
  --info: #2563eb;

  /* Data Visualization */
  --data-up: #16a34a;           /* Positive values */
  --data-down: #ef4444;         /* Negative values */
  --data-neutral: #94a3b8;      /* Neutral values */

  /* Focus Ring */
  --ring: var(--primary);
}
```

### Dark Mode Overrides

```css
[data-theme="dark"] {
  /* Surfaces */
  --bg: #0f0f0f;
  --content: #f5f5f5;
  --surface: #141414;
  --surface-hover: #1a1a1a;
  --border: #2a2a2a;
  --muted: #a3a3a3;

  /* Adjusted for contrast */
  --success: #22c55e;
  --warning: #f59e0b;
  --danger: #f87171;
  --info: #60a5fa;
}
```

## Tailwind v4 Theme Mapping

```css
@theme inline {
  /* Colors */
  --color-background: var(--bg);
  --color-foreground: var(--content);
  --color-primary: var(--primary);
  --color-primary-foreground: var(--primary-fg);
  --color-accent: var(--accent);
  --color-accent-foreground: var(--accent-fg);
  --color-surface: var(--surface);
  --color-surface-hover: var(--surface-hover);
  --color-border: var(--border);
  --color-muted: var(--muted);

  /* Status */
  --color-success: var(--success);
  --color-warning: var(--warning);
  --color-danger: var(--danger);
  --color-info: var(--info);

  /* Data */
  --color-data-up: var(--data-up);
  --color-data-down: var(--data-down);

  /* Typography */
  --font-sans: var(--app-font-sans);
  --font-serif: var(--app-font-serif);
}
```

## Semantic Usage

### Surface Hierarchy

```tsx
// Level 0: Page background
<div className="bg-background">

  // Level 1: Cards, panels
  <div className="bg-surface border border-border">

    // Level 2: Nested elements
    <div className="bg-surface-hover">
```

### Text Hierarchy

```tsx
<h1 className="text-foreground">Primary text</h1>
<p className="text-muted">Secondary/helper text</p>
<span className="text-primary">Emphasized text</span>
```

### Status Indicators

```tsx
<span className="text-success">Success message</span>
<span className="text-warning">Warning message</span>
<span className="text-danger">Error message</span>
<span className="text-info">Info message</span>
```

### Data Visualization

```tsx
// For financial data
<span className={cn(
  value > 0 && "text-data-up",
  value < 0 && "text-data-down",
  value === 0 && "text-data-neutral"
)}>
  {formatCurrency(value)}
</span>
```

## Soft Variants

For subtle backgrounds (badges, alerts), use `color-mix`:

```css
:root {
  --soft-alpha: 14%;  /* Light mode */
}

[data-theme="dark"] {
  --soft-alpha: 28%;  /* Stronger in dark mode */
}
```

```tsx
// Soft primary background
className="bg-[color-mix(in_srgb,var(--primary)_var(--soft-alpha),var(--surface))]"

// Soft danger background
className="bg-[color-mix(in_srgb,var(--danger)_var(--soft-alpha),var(--surface))]"
```

## Gradients

```css
:root {
  --grad-hero: linear-gradient(135deg, var(--primary), var(--accent));
  --grad-cta: linear-gradient(90deg, var(--primary), var(--accent));
}

@layer utilities {
  .bg-hero {
    background-image: var(--grad-hero);
  }
  .bg-cta {
    background-image: var(--grad-cta);
  }
}
```

## Focus States

Consistent focus ring for all interactive elements:

```css
.focus-ring {
  @apply focus-visible:outline-2
         focus-visible:outline-offset-2
         focus-visible:outline-[var(--ring)];
}
```

```tsx
<button className="focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--ring)]">
  Interactive
</button>
```

## Best Practices

### DO:
- Use semantic tokens (`bg-primary`, `text-foreground`)
- Define new tokens in CSS variables
- Test in both light and dark modes
- Use `color-mix` for transparency

### DON'T:
- Use hardcoded colors (`bg-blue-500`)
- Use opacity for theme colors (`bg-blue-500/50`)
- Forget dark mode variants
- Mix semantic and non-semantic tokens
