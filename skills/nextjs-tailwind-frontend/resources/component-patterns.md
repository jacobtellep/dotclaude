# Component Patterns

## TypeScript Props Pattern

Always extend the appropriate HTML element props:

```tsx
// For div-based components
export interface CardProps extends React.ComponentPropsWithoutRef<"div"> {
  elevated?: boolean;
  interactive?: boolean;
}

// For button components
export interface ButtonProps extends React.ComponentPropsWithoutRef<"button"> {
  variant?: "solid" | "outline" | "plain";
  size?: "sm" | "md" | "lg";
}

// For inputs
export interface InputProps extends React.ComponentPropsWithoutRef<"input"> {
  label?: string;
  error?: string;
}
```

## Compound Components

Group related components that share context:

```tsx
// card.tsx
import { cn } from "@/lib/cn";

export interface CardProps extends React.ComponentPropsWithoutRef<"div"> {
  elevated?: boolean;
  interactive?: boolean;
}

export function Card({
  className,
  elevated,
  interactive,
  ...props
}: CardProps) {
  return (
    <div
      className={cn(
        "rounded-lg border border-border bg-surface",
        elevated && "shadow-lg",
        interactive && "cursor-pointer hover:bg-surface-hover transition-colors",
        className
      )}
      {...props}
    />
  );
}

export function CardHeader({
  className,
  ...props
}: React.ComponentPropsWithoutRef<"div">) {
  return (
    <div
      className={cn("flex flex-col gap-y-1.5 px-6 py-4", className)}
      {...props}
    />
  );
}

export function CardTitle({
  className,
  ...props
}: React.ComponentPropsWithoutRef<"h3">) {
  return (
    <h3
      className={cn("text-lg font-semibold text-foreground", className)}
      {...props}
    />
  );
}

export function CardDescription({
  className,
  ...props
}: React.ComponentPropsWithoutRef<"p">) {
  return (
    <p className={cn("text-sm text-muted", className)} {...props} />
  );
}

export function CardContent({
  className,
  ...props
}: React.ComponentPropsWithoutRef<"div">) {
  return <div className={cn("px-6 py-4", className)} {...props} />;
}

export function CardFooter({
  className,
  ...props
}: React.ComponentPropsWithoutRef<"div">) {
  return (
    <div
      className={cn("flex items-center px-6 py-4 border-t border-border", className)}
      {...props}
    />
  );
}
```

### Usage:

```tsx
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from "@/components/ui/card";

<Card elevated>
  <CardHeader>
    <CardTitle>Premium Analytics</CardTitle>
    <CardDescription>Track your options performance</CardDescription>
  </CardHeader>
  <CardContent>
    <p>Your ROI this month: 12.5%</p>
  </CardContent>
  <CardFooter>
    <Button>View Details</Button>
  </CardFooter>
</Card>
```

## Polymorphic Components

Components that render as different elements based on props:

```tsx
import React from "react";
import { cn } from "@/lib/cn";

type CommonProps = {
  variant?: "solid" | "outline" | "plain";
  color?: "primary" | "accent" | "light";
  size?: "sm" | "md";
  className?: string;
  children?: React.ReactNode;
};

type AnchorProps = CommonProps & {
  href: string;
} & Omit<React.AnchorHTMLAttributes<HTMLAnchorElement>, keyof CommonProps>;

type ButtonLikeProps = CommonProps & {
  href?: never;
} & Omit<React.ButtonHTMLAttributes<HTMLButtonElement>, keyof CommonProps>;

type ButtonProps = AnchorProps | ButtonLikeProps;

const base = [
  "inline-flex items-center justify-center gap-x-2",
  "rounded-md font-medium transition-colors",
  "focus-visible:outline-2 focus-visible:outline-offset-2",
];

const sizes = {
  sm: "px-3 py-1.5 text-sm",
  md: "px-4 py-2 text-base",
};

const variants = {
  solid: {
    primary: "bg-primary text-primary-foreground hover:bg-primary/90",
    accent: "bg-accent text-accent-foreground hover:bg-accent/90",
    light: "bg-surface text-foreground hover:bg-surface-hover",
  },
  outline: {
    primary: "border border-primary text-primary hover:bg-primary/10",
    accent: "border border-accent text-accent hover:bg-accent/10",
    light: "border border-border text-foreground hover:bg-surface-hover",
  },
  plain: {
    primary: "text-primary hover:bg-primary/10",
    accent: "text-accent hover:bg-accent/10",
    light: "text-foreground hover:bg-surface-hover",
  },
};

export const Button = React.forwardRef<HTMLElement, ButtonProps>(
  function Button(
    {
      variant = "solid",
      color = "primary",
      size = "md",
      className,
      ...props
    },
    ref
  ) {
    const classes = cn(base, sizes[size], variants[variant][color], className);

    // Type guard for anchor vs button
    if ("href" in props && typeof props.href === "string") {
      return (
        <a
          ref={ref as React.ForwardedRef<HTMLAnchorElement>}
          className={classes}
          {...(props as AnchorProps)}
        />
      );
    }

    return (
      <button
        ref={ref as React.ForwardedRef<HTMLButtonElement>}
        className={classes}
        {...(props as ButtonLikeProps)}
      />
    );
  }
);
```

### Usage:

```tsx
// Renders as <a>
<Button href="/signup" color="accent">Sign Up</Button>

// Renders as <button>
<Button onClick={handleClick} variant="outline">Cancel</Button>
```

## Variant Mapping Pattern

For components with multiple variants across multiple colors:

```tsx
type BadgeVariant = "solid" | "soft" | "outline";
type BadgeColor = "neutral" | "primary" | "accent" | "success" | "warning" | "danger" | "info";

const variants: Record<BadgeVariant, Record<BadgeColor, string>> = {
  solid: {
    neutral: "bg-muted/20 text-foreground",
    primary: "bg-primary text-primary-foreground",
    accent: "bg-accent text-accent-foreground",
    success: "bg-success text-white",
    warning: "bg-warning text-white",
    danger: "bg-danger text-white",
    info: "bg-info text-white",
  },
  soft: {
    neutral: "bg-muted/10 text-muted",
    primary: "bg-[color-mix(in_srgb,var(--primary)_14%,var(--surface))] text-primary",
    accent: "bg-[color-mix(in_srgb,var(--accent)_14%,var(--surface))] text-accent",
    success: "bg-[color-mix(in_srgb,var(--success)_14%,var(--surface))] text-success",
    warning: "bg-[color-mix(in_srgb,var(--warning)_14%,var(--surface))] text-warning",
    danger: "bg-[color-mix(in_srgb,var(--danger)_14%,var(--surface))] text-danger",
    info: "bg-[color-mix(in_srgb,var(--info)_14%,var(--surface))] text-info",
  },
  outline: {
    neutral: "border border-border text-foreground",
    primary: "border border-primary text-primary",
    // ... etc
  },
};

export function Badge({ variant = "soft", color = "neutral", className, ...props }) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium",
        variants[variant][color],
        className
      )}
      {...props}
    />
  );
}
```

## CSS Variable Slots

For dynamic styling within a component:

```tsx
const toneVars: Record<AlertTone, string> = {
  info: "[--_bg:color-mix(in_srgb,var(--info)_14%,var(--surface))] [--_border:var(--info)] [--_fg:var(--info)]",
  success: "[--_bg:color-mix(in_srgb,var(--success)_14%,var(--surface))] [--_border:var(--success)] [--_fg:var(--success)]",
  warning: "[--_bg:color-mix(in_srgb,var(--warning)_14%,var(--surface))] [--_border:var(--warning)] [--_fg:var(--warning)]",
  danger: "[--_bg:color-mix(in_srgb,var(--danger)_14%,var(--surface))] [--_border:var(--danger)] [--_fg:var(--danger)]",
};

export function Alert({ tone = "info", className, children, ...props }) {
  return (
    <div
      role="alert"
      className={cn(
        "rounded-lg border px-4 py-3",
        toneVars[tone],
        "bg-[var(--_bg)] border-[var(--_border)] text-[var(--_fg)]",
        className
      )}
      {...props}
    >
      {children}
    </div>
  );
}
```

## Data-Slot Pattern

Use data attributes for icon positioning:

```tsx
export function Input({ icon, className, ...props }) {
  return (
    <span
      data-slot="control"
      className={cn(
        "relative block",
        // Adjust padding when icon is present
        "has-[[data-slot=icon]:first-child]:[&_input]:pl-10",
        className
      )}
    >
      {icon && (
        <span data-slot="icon" className="absolute left-3 top-1/2 -translate-y-1/2 text-muted">
          {icon}
        </span>
      )}
      <input
        className="w-full rounded-md border border-border bg-surface px-3 py-2"
        {...props}
      />
    </span>
  );
}
```

## forwardRef Pattern

Always forward refs for controlled components:

```tsx
export const Input = React.forwardRef<HTMLInputElement, InputProps>(
  function Input({ label, error, className, ...props }, ref) {
    return (
      <div>
        {label && <label className="text-sm font-medium">{label}</label>}
        <input
          ref={ref}
          className={cn(
            "w-full rounded-md border px-3 py-2",
            error ? "border-danger" : "border-border",
            className
          )}
          {...props}
        />
        {error && <p className="text-sm text-danger">{error}</p>}
      </div>
    );
  }
);
```
