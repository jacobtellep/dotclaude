---
name: nextjs-tailwind-frontend
description: Next.js/React/Tailwind CSS development patterns for modern frontend applications. Use when creating components, pages, styling with Tailwind v4, working with CSS variables and design tokens, implementing dark mode, using Headless UI, or building with Next.js App Router. Covers compound components, polymorphic patterns, theme management, and TypeScript best practices.
---

# Next.js/Tailwind Frontend Development Guidelines

## Purpose

Establish consistency and best practices for Next.js applications using Tailwind CSS v4, Headless UI, and TypeScript with a CSS-variable-first design system.

## When to Use This Skill

Automatically activates when working on:
- Creating React components
- Styling with Tailwind CSS
- Building pages with Next.js App Router
- Implementing dark mode/theme switching
- Working with Headless UI components
- Design token/CSS variable systems

---

## Quick Start

### New Component Checklist

- [ ] **File Location**: `components/ui/` for reusable, `app/` for pages
- [ ] **TypeScript**: Props interface extending HTML element props
- [ ] **Styling**: Tailwind classes using semantic tokens
- [ ] **Dark Mode**: Uses CSS variables that adapt to theme
- [ ] **Accessibility**: Keyboard navigation, ARIA attributes

---

## Architecture Overview

### Directory Structure

```
app/                        # Next.js App Router
├── globals.css             # Design tokens + Tailwind theme
├── layout.tsx              # Root layout (fonts, theme provider)
├── page.tsx                # Homepage
└── [feature]/page.tsx      # Feature pages

components/
├── theme-provider.tsx      # Dark/light theme context
└── ui/                     # Reusable component library
    ├── index.ts            # Barrel export
    ├── button.tsx
    ├── card.tsx
    ├── input.tsx
    └── ...

lib/
└── cn.ts                   # className utility
```

---

## Design System

### CSS Variables First

Define tokens in `:root` and `[data-theme="dark"]`, then expose via Tailwind:

```css
/* app/globals.css */
:root {
  --primary: #BFB571;
  --accent: #EC6F66;
  --bg: #ffffff;
  --content: #222222;
  --surface: #fafafa;
  --border: #e6e6e6;

  /* Status colors */
  --success: #16a34a;
  --warning: #d97706;
  --danger: #dc2626;
  --info: #2563eb;
}

[data-theme="dark"] {
  --bg: #0f0f0f;
  --content: #f5f5f5;
  --surface: #141414;
  /* Adjusted for dark contrast */
}

/* Expose to Tailwind v4 */
@theme inline {
  --color-background: var(--bg);
  --color-foreground: var(--content);
  --color-primary: var(--primary);
  --color-surface: var(--surface);
  --font-sans: var(--app-font-sans);
}
```

### Semantic Token Usage

```tsx
// Use semantic tokens, not hardcoded colors
<div className="bg-background text-foreground">
  <button className="bg-primary text-primary-foreground">
    Action
  </button>
  <div className="bg-surface border-border">
    Card content
  </div>
</div>
```

See [design-tokens.md](resources/design-tokens.md) for complete token reference.

---

## Component Patterns

### 1. Compound Components

Group related components that work together:

```tsx
// components/ui/card.tsx
export function Card({ className, elevated, ...props }) {
  return (
    <div
      className={cn(
        "rounded-lg border border-border bg-surface",
        elevated && "shadow-lg",
        className
      )}
      {...props}
    />
  );
}

export function CardHeader({ className, ...props }) {
  return <div className={cn("px-6 py-4", className)} {...props} />;
}

export function CardTitle({ className, ...props }) {
  return <h3 className={cn("text-lg font-semibold", className)} {...props} />;
}

export function CardContent({ className, ...props }) {
  return <div className={cn("px-6 py-4", className)} {...props} />;
}

// Usage
<Card elevated>
  <CardHeader>
    <CardTitle>Title</CardTitle>
  </CardHeader>
  <CardContent>Content</CardContent>
</Card>
```

### 2. Polymorphic Components

Components that render as different elements:

```tsx
type ButtonProps = {
  variant?: 'solid' | 'outline' | 'plain';
  color?: 'primary' | 'accent';
} & (
  | { href: string } & React.AnchorHTMLAttributes<HTMLAnchorElement>
  | { href?: never } & React.ButtonHTMLAttributes<HTMLButtonElement>
);

export const Button = React.forwardRef<HTMLElement, ButtonProps>(
  function Button({ href, variant = 'solid', color = 'primary', ...props }, ref) {
    const classes = cn(baseStyles, variants[variant][color]);

    if (href) {
      return <a ref={ref} href={href} className={classes} {...props} />;
    }
    return <button ref={ref} className={classes} {...props} />;
  }
);

// Usage - renders as <a> or <button>
<Button href="/path">Link</Button>
<Button onClick={handler}>Action</Button>
```

### 3. Variant Mapping

```tsx
const variants = {
  solid: {
    primary: "bg-primary text-primary-foreground hover:bg-primary/90",
    accent: "bg-accent text-accent-foreground hover:bg-accent/90",
  },
  outline: {
    primary: "border-primary text-primary hover:bg-primary/10",
    accent: "border-accent text-accent hover:bg-accent/10",
  },
};

// Apply with cn()
className={cn(base, variants[variant][color], className)}
```

See [component-patterns.md](resources/component-patterns.md) for more.

---

## Tailwind v4 Specifics

### @theme inline

Tailwind v4 uses `@theme inline` to define CSS variable mappings:

```css
@theme inline {
  --color-primary: var(--primary);
  --color-background: var(--bg);
  --font-sans: var(--app-font-sans);
}
```

### color-mix for Soft Variants

```css
/* Soft background with opacity */
.bg-primary-soft {
  background: color-mix(in srgb, var(--primary) 14%, var(--surface));
}

/* In Tailwind class */
className="bg-[color-mix(in_srgb,var(--primary)_14%,var(--surface))]"
```

See [tailwind-v4.md](resources/tailwind-v4.md) for migration notes.

---

## Theme Management

### Theme Provider

```tsx
// components/theme-provider.tsx
"use client";

export type Theme = "light" | "dark" | "system";

const ThemeContext = createContext<{
  theme: Theme;
  setTheme: (theme: Theme) => void;
}>(null);

export function ThemeProvider({ children }) {
  const [theme, setTheme] = useState<Theme>("system");

  useEffect(() => {
    const isDark = theme === "dark" ||
      (theme === "system" &&
       window.matchMedia("(prefers-color-scheme: dark)").matches);

    document.documentElement.setAttribute(
      "data-theme",
      isDark ? "dark" : "light"
    );
  }, [theme]);

  return (
    <ThemeContext.Provider value={{ theme, setTheme }}>
      {children}
    </ThemeContext.Provider>
  );
}

export const useTheme = () => useContext(ThemeContext);
```

### Usage

```tsx
function ThemeToggle() {
  const { theme, setTheme } = useTheme();

  return (
    <button onClick={() => setTheme(theme === "dark" ? "light" : "dark")}>
      Toggle Theme
    </button>
  );
}
```

---

## className Utility

```typescript
// lib/cn.ts
type ClassValue = string | number | boolean | null | undefined | ClassValue[];

export function cn(...inputs: ClassValue[]): string {
  return inputs
    .flat(Infinity)
    .filter((x) => typeof x === "string" && x.length > 0)
    .join(" ")
    .replace(/\s+/g, " ")
    .trim();
}

// Usage
cn("base", condition && "conditional", className)
```

---

## Headless UI Integration

Wrap Headless UI components with Tailwind styling:

```tsx
import { Dialog, DialogPanel } from "@headlessui/react";

export function Modal({ open, onClose, children }) {
  return (
    <Dialog open={open} onClose={onClose} className="relative z-50">
      {/* Backdrop */}
      <div className="fixed inset-0 bg-black/30" aria-hidden="true" />

      {/* Panel */}
      <div className="fixed inset-0 flex items-center justify-center p-4">
        <DialogPanel className="bg-surface rounded-lg p-6 max-w-md">
          {children}
        </DialogPanel>
      </div>
    </Dialog>
  );
}
```

---

## Next.js App Router

### Layout with Fonts

```tsx
// app/layout.tsx
import { Poppins, Lora } from "next/font/google";
import { ThemeProvider } from "@/components/theme-provider";

const poppins = Poppins({
  variable: "--app-font-sans",
  subsets: ["latin"],
  display: "swap",
  weight: ["400", "500", "600", "700"],
});

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body className={`${poppins.variable} font-sans antialiased`}>
        <ThemeProvider>{children}</ThemeProvider>
      </body>
    </html>
  );
}
```

### Client Components

```tsx
"use client";

import { useState } from "react";

export function InteractiveComponent() {
  const [count, setCount] = useState(0);
  return <button onClick={() => setCount(c => c + 1)}>{count}</button>;
}
```

---

## Anti-Patterns to Avoid

❌ Hardcoded colors (`bg-blue-500` instead of `bg-primary`)
❌ Inline styles for themeable properties
❌ Missing dark mode support
❌ Non-semantic class names
❌ Missing TypeScript props interfaces
❌ Missing keyboard navigation

---

## Navigation Guide

| Need to... | Read this |
|------------|-----------|
| Define design tokens | [design-tokens.md](resources/design-tokens.md) |
| Build components | [component-patterns.md](resources/component-patterns.md) |
| Use Tailwind v4 features | [tailwind-v4.md](resources/tailwind-v4.md) |

---

**For complete project details, see the project's `CLAUDE.md` or `README.md` file.**
