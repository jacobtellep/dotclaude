# Prisma Database Patterns

## Setup

### Client Singleton

```typescript
// src/database/client.ts
import { PrismaClient } from '@prisma/client';

// Single instance for the application
export const prisma = new PrismaClient({
  log: process.env.NODE_ENV === 'development'
    ? ['query', 'error', 'warn']
    : ['error'],
});

// Graceful shutdown
process.on('beforeExit', async () => {
  await prisma.$disconnect();
});
```

### Usage in Services

```typescript
// Direct import - no repository layer needed for most cases
import { prisma } from '../database/client.js';

export async function getUserPositions(userId: string) {
  return prisma.position.findMany({
    where: { userId, status: 'OPEN' },
    orderBy: { expirationDate: 'asc' },
  });
}
```

## Common Operations

### Find with Relations

```typescript
const userWithPositions = await prisma.user.findUnique({
  where: { id: userId },
  include: {
    positions: {
      where: { status: 'OPEN' },
      orderBy: { createdAt: 'desc' },
    },
    brokerConnection: true,
  },
});
```

### Upsert (Update or Create)

```typescript
// Perfect for syncing external data
const position = await prisma.position.upsert({
  where: {
    userId_externalId: {
      userId: user.id,
      externalId: brokerPosition.id,
    },
  },
  create: {
    userId: user.id,
    externalId: brokerPosition.id,
    stock: brokerPosition.symbol,
    // ... other fields
  },
  update: {
    stock: brokerPosition.symbol,
    status: brokerPosition.status,
    // ... fields to update
  },
});
```

### Transactions

```typescript
// All operations succeed or all fail
const result = await prisma.$transaction(async (tx) => {
  const user = await tx.user.update({
    where: { id: userId },
    data: { lastSyncedAt: new Date() },
  });

  const positions = await tx.position.createMany({
    data: positionsToCreate,
  });

  return { user, positionsCreated: positions.count };
});
```

### Aggregations

```typescript
const stats = await prisma.position.aggregate({
  where: { userId, status: 'CLOSED' },
  _sum: {
    premium: true,
    cost: true,
  },
  _count: true,
  _avg: {
    daysHeld: true,
  },
});

// stats._sum.premium - total premium
// stats._count - number of positions
// stats._avg.daysHeld - average days held
```

### Group By

```typescript
const byMonth = await prisma.position.groupBy({
  by: ['closedMonth'],
  where: { userId, status: 'CLOSED' },
  _sum: { premium: true },
  _count: true,
  orderBy: { closedMonth: 'asc' },
});
```

## Schema Best Practices

### Financial Fields

```prisma
model Position {
  // Use Decimal for money - never Float
  premium      Decimal @db.Decimal(10, 2)
  strikePrice  Decimal @db.Decimal(10, 2)
  cost         Decimal @db.Decimal(10, 2)
}
```

### Indexes

```prisma
model Position {
  id        String   @id @default(uuid())
  userId    String
  status    String
  expirationDate DateTime

  // High-frequency query patterns
  @@index([userId])
  @@index([userId, status])
  @@index([userId, expirationDate])

  // Unique constraint for external sync
  @@unique([userId, externalId])
}
```

### Audit Timestamps

```prisma
model Position {
  createdAt    DateTime @default(now())
  updatedAt    DateTime @updatedAt
  lastSyncedAt DateTime?  // For external sync tracking
}
```

## After Schema Changes

**Always run these commands:**

```bash
# 1. Regenerate Prisma client (REQUIRED)
npm run db:generate

# 2. Create migration
npm run db:migrate

# 3. For production deployment
npx prisma migrate deploy
```

## Testing

### Test Database Setup

```typescript
// tests/setup.ts
import { PrismaClient } from '@prisma/client';

const prisma = new PrismaClient({
  datasources: {
    db: {
      url: 'file:./test.db',  // SQLite for tests
    },
  },
});

beforeAll(async () => {
  await prisma.$connect();
});

afterAll(async () => {
  await prisma.$disconnect();
});

beforeEach(async () => {
  // Clear tables between tests
  await prisma.position.deleteMany();
  await prisma.user.deleteMany();
});
```

### Creating Test Data

```typescript
const testUser = await prisma.user.create({
  data: {
    auth0Id: 'auth0|test123',
    email: 'test@example.com',
    positions: {
      create: [
        {
          stock: 'AAPL',
          type: 'COVERED_CALL',
          status: 'OPEN',
          premium: 125.50,
          strikePrice: 150.00,
        },
      ],
    },
  },
  include: { positions: true },
});
```
