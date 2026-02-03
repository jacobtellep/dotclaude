# Tailwind CSS v4 Specifics

## Key Changes from v3

### @theme inline

In Tailwind v4, CSS variable mapping uses `@theme inline`:

```css
/* v3 (tailwind.config.js) */
module.exports = {
  theme: {
    extend: {
      colors: {
        primary: 'var(--primary)',
      },
    },
  },
};

/* v4 (globals.css) */
@theme inline {
  --color-primary: var(--primary);
  --color-background: var(--bg);
  --font-sans: var(--app-font-sans);
}
```

### PostCSS Configuration

```javascript
// postcss.config.mjs
export default {
  plugins: ["@tailwindcss/postcss"],
};
```

### No tailwind.config.js

Tailwind v4 uses CSS-first configuration. Remove `tailwind.config.js` and configure in CSS.

## CSS Variable Integration

### Defining Tokens

```css
/* Define in :root */
:root {
  --primary: #BFB571;
  --accent: #EC6F66;
  --bg: #ffffff;
}

/* Expose to Tailwind */
@theme inline {
  --color-primary: var(--primary);
  --color-accent: var(--accent);
  --color-background: var(--bg);
}

/* Now you can use: */
/* bg-primary, text-primary, border-primary, etc. */
```

### Typography

```css
@theme inline {
  --font-sans: var(--app-font-sans);
  --font-serif: var(--app-font-serif);
}

/* Usage: font-sans, font-serif */
```

## color-mix() for Transparency

Tailwind v4 works well with CSS `color-mix()`:

```css
/* Instead of opacity classes */
.bg-primary-soft {
  background: color-mix(in srgb, var(--primary) 14%, var(--surface));
}
```

In Tailwind classes (escape underscores):

```tsx
className="bg-[color-mix(in_srgb,var(--primary)_14%,var(--surface))]"
```

### Why color-mix over opacity?

```css
/* ❌ Opacity affects text readability on dark backgrounds */
.bg-primary/10 {
  /* Primary becomes very faint in dark mode */
}

/* ✅ color-mix blends with surface color */
color-mix(in srgb, var(--primary) 14%, var(--surface))
/* Adapts correctly to dark mode surface */
```

## Arbitrary Values

### Colors

```tsx
// CSS variable
className="bg-[var(--custom-color)]"

// color-mix
className="bg-[color-mix(in_srgb,var(--primary)_20%,transparent)]"

// HSL
className="bg-[hsl(210_40%_96%)]"
```

### Spacing

```tsx
className="p-[var(--card-padding)]"
className="mt-[clamp(1rem,5vw,3rem)]"
```

## @layer Utilities

Define custom utilities in the utilities layer:

```css
@layer utilities {
  .bg-hero {
    background-image: var(--grad-hero);
  }

  .text-balance {
    text-wrap: balance;
  }

  .scrollbar-hide {
    -ms-overflow-style: none;
    scrollbar-width: none;
    &::-webkit-scrollbar {
      display: none;
    }
  }
}
```

## Dark Mode with data-theme

```css
/* Base tokens */
:root {
  --bg: #ffffff;
  --content: #222222;
}

/* Dark mode tokens */
[data-theme="dark"] {
  --bg: #0f0f0f;
  --content: #f5f5f5;
}

/* Tailwind picks up the CSS variable automatically */
@theme inline {
  --color-background: var(--bg);
  --color-foreground: var(--content);
}
```

### Setting the Theme

```tsx
// In layout or theme provider
<html data-theme={isDark ? "dark" : "light"}>
```

## Modern Features

### Container Queries

```css
@layer utilities {
  .@container {
    container-type: inline-size;
  }
}
```

```tsx
<div className="@container">
  <div className="@md:flex-row flex-col">
    {/* Responds to container, not viewport */}
  </div>
</div>
```

### has() Selector

```tsx
// Parent styling based on child state
className="has-[:focus]:ring-2"
className="has-[[data-slot=icon]]:pl-10"
```

### :is() and :where()

```tsx
// Group selectors
className="hover:is-[a,button]:underline"
```

## Migration Checklist

- [ ] Remove `tailwind.config.js`
- [ ] Add `@theme inline` block in `globals.css`
- [ ] Update PostCSS config to use `@tailwindcss/postcss`
- [ ] Move color definitions to CSS variables
- [ ] Replace opacity variants with `color-mix()` where needed
- [ ] Test dark mode with `data-theme` attribute
- [ ] Update any deprecated class names

## Common Gotchas

### Escaped Underscores in Arbitrary Values

```tsx
// Spaces in color-mix need underscore escaping
className="bg-[color-mix(in_srgb,var(--primary)_14%,var(--surface))]"
//                       ^ underscores replace spaces
```

### CSS Variable Fallbacks

```css
/* Provide fallbacks for CSS variables */
color: var(--primary, #BFB571);
```

### Build Performance

Tailwind v4 is significantly faster. If you notice slowness:
- Check for circular CSS variable references
- Ensure PostCSS is configured correctly
- Clear node_modules and reinstall
