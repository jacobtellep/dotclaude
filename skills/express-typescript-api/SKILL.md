---
name: express-typescript-api
description: Express/TypeScript backend development patterns for Node.js APIs. Use when creating routes, services, middleware, or working with Prisma, Auth0 JWT authentication, Zod validation, financial calculations with Decimal.js, or ES module patterns. Covers service-oriented architecture, middleware pipeline ordering, authentication flows, and testing strategies.
---

# Express/TypeScript API Development Guidelines

## Purpose

Establish consistency and best practices for Express/TypeScript backend APIs with Auth0 authentication, Prisma ORM, and financial precision requirements.

## When to Use This Skill

Automatically activates when working on:
- Creating or modifying routes and endpoints
- Building services for business logic
- Implementing middleware (auth, validation, caching)
- Database operations with Prisma
- Input validation with Zod
- Financial calculations requiring precision
- Backend testing

---

## Quick Start

### New Feature Checklist

- [ ] **Route**: Clean definition in `routes/`, delegate to service
- [ ] **Service**: Business logic, ~15KB max per file
- [ ] **Validation**: Zod schema in `schemas/`
- [ ] **Types**: TypeScript interfaces in `types/`
- [ ] **Tests**: Unit + integration tests
- [ ] **Comments**: Extensive documentation (see Comment Requirements)

---

## Architecture Overview

### Service-Oriented Structure

```
src/
├── routes/              # API endpoint definitions
├── services/            # Business logic layer
│   └── modulename/      # Complex domains get subdirectories
├── middleware/          # Express middleware (auth, cache, validation)
├── types/               # TypeScript interfaces
├── schemas/             # Zod validation schemas
├── utils/               # Shared utilities
└── app.ts               # Express setup + middleware pipeline
```

**Key Principle:** Services encapsulate business logic. Routes delegate to services. No repository layer needed for most cases - services access Prisma directly.

---

## Critical Patterns

### 1. Middleware Pipeline Order (CRITICAL!)

**Order matters!** Authentication must come before business logic routes.

```typescript
// src/app.ts - FOLLOW THIS ORDER
// 1. Production middleware (global)
app.use(compression());
app.use(helmet());
app.use(cors(corsOptions));
app.use(morgan('combined'));

// 2. Express core
app.use(express.json({ limit: '10mb' }));
app.use(express.urlencoded({ extended: true }));

// 3. Public routes (NO AUTH)
app.use('/health', healthRoutes);
app.use('/webhooks', webhookRoutes);

// 4. Protected routes (WITH AUTH)
app.use('/api', rateLimiter);
app.use('/api', authMiddleware);    // JWT validation
app.use('/api', userMiddleware);    // User context
app.use('/api/positions', positionRoutes);
app.use('/api/analytics', analyticsRoutes);

// 5. Error handling (LAST)
app.use(notFoundHandler);
app.use(globalErrorHandler);
```

See [middleware-order.md](resources/middleware-order.md) for complete details.

### 2. Auth0 JWT Authentication

```typescript
// Middleware validates JWT using Auth0 JWKS
// Request enriched with req.auth (JWT payload) and req.user (database user)

// Route access:
router.get('/profile', (req, res) => {
  const user = req.user; // EnhancedAuthUser with Auth0 + DB data
  return successResponse(user);
});
```

See [auth0-patterns.md](resources/auth0-patterns.md) for authentication flow.

### 3. Financial Precision with Decimal.js

**NEVER use JavaScript `Number` for money.** Always use `Decimal`:

```typescript
import { Decimal } from 'decimal.js';

// Correct - maintains precision
const premium = new Decimal('125.50');
const cost = new Decimal('5000');
const roi = premium.div(cost).mul(100); // 2.51%

// WRONG - loses precision
const badROI = (125.50 / 5000) * 100; // Floating point errors
```

See [financial-precision.md](resources/financial-precision.md) for patterns.

### 4. ES Module Imports

This project uses ES modules. **Always use `.js` extensions**:

```typescript
// ✅ Correct
import { service } from './service.js';
import { User } from '../types/user.js';

// ❌ Wrong - will fail at runtime
import { service } from './service';
```

### 5. API Response Format

All endpoints return consistent `ApiResponse<T>`:

```typescript
{
  "success": boolean,
  "data"?: T,           // Only on success
  "error"?: string,     // Only on failure
  "timestamp": string   // ISO 8601
}

// Helpers
return successResponse(data);
return errorResponse('message', 500);
```

### 6. Zod Validation

```typescript
// schemas/position.ts
import { z } from 'zod';

export const createPositionSchema = z.object({
  stock: z.string().min(1).max(10),
  strikePrice: z.number().positive(),
  premium: z.number().nonnegative(),
  expirationDate: z.string().datetime(),
});

// In route
const validated = createPositionSchema.parse(req.body);
```

---

## Comment Requirements

**This is a financial application.** All code must have extensive comments:

### Function Documentation
```typescript
/**
 * Maps raw broker position data to database schema
 *
 * @param raw - Raw position from broker API
 * @param accountInfo - Account tracking information
 * @returns Mapped position ready for database upsert
 *
 * Key transformations:
 * - Detects option positions vs stock positions
 * - Classifies as COVERED_CALL or CASH_SECURED_PUT
 * - Handles option multiplier (typically 100 shares)
 */
```

### Complex Logic
- Explain WHY this approach was chosen
- Step-by-step for non-obvious logic
- Document edge cases and business rules

### Financial Calculations
- Show the formula being used
- Explain Decimal operations
- Include example calculations

---

## Database Patterns

### Prisma Direct Access

```typescript
// Services access Prisma directly
import { prisma } from '../database/client.js';

export async function getUserPositions(userId: string) {
  return prisma.position.findMany({
    where: { userId, status: 'OPEN' },
    orderBy: { expirationDate: 'asc' },
  });
}
```

### After Schema Changes

**MUST run after any `schema.prisma` change:**
```bash
npm run db:generate   # Regenerate Prisma client
npm run db:migrate    # Create migration
```

See [prisma-patterns.md](resources/prisma-patterns.md) for more.

---

## Testing Patterns

```bash
npm test             # Run all tests
npm run test:watch   # Watch mode
npm run test:ui      # Interactive UI

# Specific file
npx vitest run tests/unit/calculations.test.ts
```

### Test Organization
- `tests/unit/` - Services, utilities, calculations
- `tests/integration/` - Full API endpoint flows

**Coverage threshold:** 80% for branches, functions, lines, statements

---

## Anti-Patterns to Avoid

❌ Business logic in routes (delegate to services)
❌ JavaScript `Number` for money (use Decimal)
❌ Missing `.js` extensions in imports
❌ Middleware in wrong order (auth before protected routes)
❌ Missing comments on financial logic
❌ Direct `process.env` access (use config module)

---

## Navigation Guide

| Need to... | Read this |
|------------|-----------|
| Understand middleware order | [middleware-order.md](resources/middleware-order.md) |
| Implement authentication | [auth0-patterns.md](resources/auth0-patterns.md) |
| Work with database | [prisma-patterns.md](resources/prisma-patterns.md) |
| Handle money/calculations | [financial-precision.md](resources/financial-precision.md) |

---

**For complete architecture details, see the project's `CLAUDE.md` file.**
