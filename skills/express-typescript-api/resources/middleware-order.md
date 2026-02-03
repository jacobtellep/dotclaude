# Middleware Pipeline Order

## Critical: Order Matters!

The Express middleware pipeline must follow a specific order. Changing this order can break authentication and security.

## Standard Pipeline Order

```typescript
// ═══════════════════════════════════════════════════════════════
// SECTION 1: GLOBAL MIDDLEWARE (All Requests)
// ═══════════════════════════════════════════════════════════════

// Compression - reduce response sizes
app.use(compression());

// Security headers - Helmet.js provides 15+ security headers
app.use(helmet({
  contentSecurityPolicy: false,  // Adjust based on needs
  crossOriginEmbedderPolicy: false,
}));

// CORS - whitelist trusted origins
app.use(cors({
  origin: ['https://yourdomain.com', 'http://localhost:3000'],
  credentials: true,
}));

// Request logging
app.use(morgan('combined'));

// ═══════════════════════════════════════════════════════════════
// SECTION 2: EXPRESS CORE PARSERS
// ═══════════════════════════════════════════════════════════════

// JSON body parser with size limit
app.use(express.json({ limit: '10mb' }));

// URL-encoded form data
app.use(express.urlencoded({ extended: true }));

// ═══════════════════════════════════════════════════════════════
// SECTION 3: LEGACY SECURITY HEADERS (Optional)
// ═══════════════════════════════════════════════════════════════

app.use((req, res, next) => {
  res.setHeader('X-Content-Type-Options', 'nosniff');
  res.setHeader('X-Frame-Options', 'DENY');
  res.setHeader('X-XSS-Protection', '1; mode=block');
  next();
});

// ═══════════════════════════════════════════════════════════════
// SECTION 4: PUBLIC ROUTES (No Authentication)
// ═══════════════════════════════════════════════════════════════

// Health check - required for load balancers/Railway
app.use('/health', healthRoutes);

// Webhooks - external services (Stripe, SnapTrade)
// Must be before auth middleware!
app.use('/webhooks', webhookRoutes);

// OAuth callbacks (if applicable)
app.get('/oauth/callback', oauthCallbackHandler);

// ═══════════════════════════════════════════════════════════════
// SECTION 5: PROTECTED ROUTES (Authentication Required)
// ═══════════════════════════════════════════════════════════════

// Rate limiting - prevent abuse (before auth to protect auth endpoint)
app.use('/api', rateLimiter);

// JWT Authentication - validates token, adds req.auth
app.use('/api', authMiddleware);

// User Context - fetches/creates DB user, adds req.user
app.use('/api', userMiddleware);

// Business Logic Routes
app.use('/api/positions', positionRoutes);
app.use('/api/analytics', analyticsRoutes);
app.use('/api/subscription', subscriptionRoutes);
app.use('/api/snaptrade', snaptradeRoutes);

// ═══════════════════════════════════════════════════════════════
// SECTION 6: ERROR HANDLING (Must Be Last)
// ═══════════════════════════════════════════════════════════════

// CORS error handler
app.use(corsErrorHandler);

// Auth error handler
app.use(authErrorHandler);

// 404 Not Found
app.use((req, res) => {
  res.status(404).json({
    success: false,
    error: 'Not Found',
    timestamp: new Date().toISOString(),
  });
});

// Global error handler (catch-all)
app.use((err, req, res, next) => {
  console.error(err.stack);
  res.status(500).json({
    success: false,
    error: 'Internal Server Error',
    timestamp: new Date().toISOString(),
  });
});
```

## Common Mistakes

### ❌ Auth Middleware Before Public Routes
```typescript
// WRONG - webhooks will fail
app.use(authMiddleware);
app.use('/webhooks', webhookRoutes); // 401 Unauthorized!
```

### ❌ Error Handler Before Routes
```typescript
// WRONG - errors won't be caught
app.use(errorHandler);
app.use('/api', routes); // Errors bypass handler!
```

### ❌ Rate Limiter After Auth
```typescript
// WRONG - auth endpoint unprotected
app.use('/api', authMiddleware);
app.use('/api', rateLimiter); // Too late for auth attacks
```

## Adding New Middleware

1. Determine if it needs auth context
2. If NO → Place in Section 4 (Public Routes)
3. If YES → Place in Section 5 (after userMiddleware)
4. Error handling middleware → Always Section 6
