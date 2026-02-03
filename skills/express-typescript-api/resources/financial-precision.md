# Financial Precision with Decimal.js

## Why Decimal.js?

JavaScript's `Number` type uses IEEE 754 floating-point, which causes precision errors:

```javascript
// ❌ WRONG - Floating point errors
0.1 + 0.2 === 0.3  // false! (0.30000000000000004)
125.50 * 100       // 12549.999999999998
```

For financial applications, **always use Decimal.js**:

```typescript
import { Decimal } from 'decimal.js';

// ✅ CORRECT - Exact precision
new Decimal('0.1').plus('0.2').equals('0.3')  // true
new Decimal('125.50').mul(100).toString()     // "12550"
```

## Basic Operations

```typescript
import { Decimal } from 'decimal.js';

// Creating Decimals - prefer string input for exact values
const premium = new Decimal('125.50');
const cost = new Decimal('5000');
const shares = new Decimal(100);

// Arithmetic
const total = premium.plus(50);           // Addition
const net = premium.minus(fees);          // Subtraction
const gross = premium.mul(shares);        // Multiplication
const perShare = premium.div(shares);     // Division

// Comparisons
premium.greaterThan(100)    // true
premium.lessThan(200)       // true
premium.equals('125.50')    // true

// Conversion
premium.toNumber()          // 125.5 (use sparingly)
premium.toString()          // "125.5"
premium.toFixed(2)          // "125.50"
```

## Common Financial Calculations

### ROI (Return on Investment)

```typescript
/**
 * Calculate ROI percentage
 *
 * Formula: (premium / cost) * 100
 * Example: $125.50 premium on $5000 cost = 2.51% ROI
 */
function calculateROI(premium: Decimal, cost: Decimal): Decimal {
  if (cost.isZero()) {
    return new Decimal(0);
  }
  return premium.div(cost).mul(100);
}

// Usage
const roi = calculateROI(
  new Decimal('125.50'),
  new Decimal('5000')
);
console.log(roi.toFixed(2)); // "2.51"
```

### Annualized ROI

```typescript
/**
 * Annualize ROI based on days held
 *
 * Formula: (ROI / daysHeld) * 365
 * Example: 2.51% ROI over 30 days = 30.54% annualized
 */
function annualizeROI(roi: Decimal, daysHeld: number): Decimal {
  if (daysHeld <= 0) {
    return new Decimal(0);
  }
  return roi.div(daysHeld).mul(365);
}

// Usage
const annual = annualizeROI(new Decimal('2.51'), 30);
console.log(annual.toFixed(2)); // "30.54"
```

### Options Premium Calculation

```typescript
/**
 * Calculate total premium for option position
 *
 * Options typically represent 100 shares per contract
 * Premium is quoted per share
 *
 * Formula: premiumPerShare * optionMultiplier * numberOfContracts
 * Example: $1.25/share * 100 shares * 1 contract = $125.00
 */
function calculateTotalPremium(
  premiumPerShare: Decimal,
  optionMultiplier: number = 100,
  contracts: number = 1
): Decimal {
  return premiumPerShare
    .mul(optionMultiplier)
    .mul(contracts);
}

// Usage
const totalPremium = calculateTotalPremium(
  new Decimal('1.25'),
  100,
  1
);
console.log(totalPremium.toString()); // "125"
```

### Breakeven Calculation

```typescript
/**
 * Calculate breakeven price for covered call
 *
 * Formula: costBasis - premiumReceived
 * Example: $150 stock - $1.25 premium = $148.75 breakeven
 */
function calculateBreakeven(
  costBasis: Decimal,
  premiumReceived: Decimal
): Decimal {
  return costBasis.minus(premiumReceived);
}
```

### Win Rate

```typescript
/**
 * Calculate win rate percentage
 *
 * Formula: (winners / total) * 100
 */
function calculateWinRate(winners: number, total: number): Decimal {
  if (total === 0) {
    return new Decimal(0);
  }
  return new Decimal(winners).div(total).mul(100);
}

// Usage
const winRate = calculateWinRate(45, 50);
console.log(winRate.toFixed(1)); // "90.0"
```

## Database Integration

### Storing Decimals in Prisma

```prisma
// schema.prisma
model Position {
  premium     Decimal @db.Decimal(10, 2)
  strikePrice Decimal @db.Decimal(10, 2)
  cost        Decimal @db.Decimal(10, 2)
}
```

### Converting Prisma Decimal

Prisma returns its own Decimal type. Convert to decimal.js:

```typescript
import { Decimal } from 'decimal.js';
import type { Prisma } from '@prisma/client';

// Prisma Decimal → decimal.js Decimal
function toDecimal(value: Prisma.Decimal | null): Decimal {
  return value ? new Decimal(value.toString()) : new Decimal(0);
}

// Usage
const position = await prisma.position.findFirst();
const premium = toDecimal(position.premium);
const roi = calculateROI(premium, toDecimal(position.cost));
```

## Formatting for Display

```typescript
/**
 * Format decimal as currency
 */
function formatCurrency(value: Decimal): string {
  return `$${value.toFixed(2)}`;
}

/**
 * Format decimal as percentage
 */
function formatPercent(value: Decimal, decimals: number = 2): string {
  return `${value.toFixed(decimals)}%`;
}

// Usage
console.log(formatCurrency(new Decimal('1234.50')));  // "$1234.50"
console.log(formatPercent(new Decimal('12.345')));   // "12.35%"
```

## Testing Financial Calculations

```typescript
import { describe, it, expect } from 'vitest';
import { Decimal } from 'decimal.js';

describe('Financial Calculations', () => {
  it('calculates ROI correctly', () => {
    const roi = calculateROI(
      new Decimal('125.50'),
      new Decimal('5000')
    );

    // Use toFixed for comparison to avoid precision issues
    expect(roi.toFixed(2)).toBe('2.51');
  });

  it('handles zero cost gracefully', () => {
    const roi = calculateROI(new Decimal('100'), new Decimal('0'));
    expect(roi.isZero()).toBe(true);
  });

  it('maintains precision in chained operations', () => {
    const result = new Decimal('100')
      .div(3)
      .mul(3);

    // Should be exactly 100, not 99.99999...
    expect(result.toString()).toBe('100');
  });
});
```

## Anti-Patterns

```typescript
// ❌ NEVER use Number for money
const premium: number = 125.50;
const roi = (premium / 5000) * 100;  // Precision errors!

// ❌ NEVER compare with ===
if (decimal === 125.50) { }  // Won't work

// ✅ Use Decimal methods
if (decimal.equals('125.50')) { }

// ❌ NEVER mix Number and Decimal without conversion
const bad = someDecimal + 100;  // Implicit conversion

// ✅ Explicit Decimal operations
const good = someDecimal.plus(100);
```
