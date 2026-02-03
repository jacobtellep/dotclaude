# Auth0 JWT Authentication Patterns

## Authentication Flow

```
1. Frontend → Auth0 Login
2. Auth0 → Returns JWT Token
3. Frontend → API Request with "Authorization: Bearer <token>"
4. authMiddleware → Validates JWT using Auth0 JWKS
5. userMiddleware → Fetches/creates DB user
6. Route → Access authenticated user via req.user
```

## Middleware Implementation

### authMiddleware

```typescript
import { expressjwt } from 'express-jwt';
import jwks from 'jwks-rsa';

export const authMiddleware = expressjwt({
  // Fetch public key from Auth0
  secret: jwks.expressJwtSecret({
    cache: true,
    rateLimit: true,
    jwksRequestsPerMinute: 5,
    jwksUri: `https://${process.env.AUTH0_DOMAIN}/.well-known/jwks.json`,
  }),

  // Validate token
  audience: process.env.AUTH0_AUDIENCE,
  issuer: `https://${process.env.AUTH0_DOMAIN}/`,
  algorithms: ['RS256'],
});

// After this middleware, req.auth contains JWT payload:
// {
//   sub: 'auth0|123456',
//   email: 'user@example.com',
//   email_verified: true,
//   iss: 'https://your-tenant.auth0.com/',
//   aud: 'your-api-identifier',
//   iat: 1234567890,
//   exp: 1234567890
// }
```

### userMiddleware

```typescript
export const userMiddleware = async (req, res, next) => {
  try {
    const auth0Id = req.auth.sub;
    const email = req.auth.email;

    // Find or create user in database
    let user = await prisma.user.findUnique({
      where: { auth0Id },
    });

    if (!user) {
      user = await prisma.user.create({
        data: {
          auth0Id,
          email,
          name: req.auth.name || email.split('@')[0],
        },
      });
    }

    // Attach to request
    req.user = {
      ...req.auth,      // JWT payload
      ...user,          // Database record
    };

    next();
  } catch (error) {
    next(error);
  }
};
```

## Using Authentication in Routes

```typescript
// req.user is EnhancedAuthUser
interface EnhancedAuthUser {
  // From JWT (req.auth)
  sub: string;           // Auth0 user ID
  email: string;
  email_verified: boolean;

  // From Database
  id: string;            // UUID
  auth0Id: string;
  name: string;
  subscriptionTier: string;
  createdAt: Date;
  updatedAt: Date;
}

// Route example
router.get('/profile', async (req, res) => {
  const userId = req.user.id;  // Database UUID
  const positions = await positionService.getByUserId(userId);
  return successResponse({ user: req.user, positions });
});
```

## Protecting Routes by Subscription Tier

```typescript
// Middleware factory
export const requireSubscription = (requiredTier: string) => {
  return async (req, res, next) => {
    const userTier = req.user.subscriptionTier;

    if (!hasAccess(userTier, requiredTier)) {
      return res.status(403).json({
        success: false,
        error: `Requires ${requiredTier} subscription`,
        timestamp: new Date().toISOString(),
      });
    }

    next();
  };
};

// Usage
router.get('/premium-analytics',
  requireSubscription('premium'),
  analyticsController.getPremiumStats
);
```

## Error Handling

```typescript
// Auth error handler middleware
export const authErrorHandler = (err, req, res, next) => {
  if (err.name === 'UnauthorizedError') {
    return res.status(401).json({
      success: false,
      error: 'Invalid or expired token',
      timestamp: new Date().toISOString(),
    });
  }
  next(err);
};
```

## Environment Variables

```env
AUTH0_DOMAIN=your-tenant.auth0.com
AUTH0_AUDIENCE=your-api-identifier
AUTH0_CLIENT_ID=your-client-id  # Optional, for M2M
AUTH0_CLIENT_SECRET=xxx         # Optional, for M2M
```

## Testing with Mock Auth

```typescript
// tests/helpers/mockAuth.ts
export const mockUser = {
  id: 'test-user-id',
  auth0Id: 'auth0|test123',
  email: 'test@example.com',
  subscriptionTier: 'free',
};

// Mock middleware for tests
export const mockAuthMiddleware = (req, res, next) => {
  req.auth = { sub: mockUser.auth0Id, email: mockUser.email };
  req.user = mockUser;
  next();
};
```
