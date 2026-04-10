FROM node:22-alpine AS builder
RUN npm install -g pnpm
WORKDIR /app

# Copy workspace manifests
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
COPY apps/auth/package.json ./apps/auth/
COPY packages/db/package.json ./packages/db/

# Install all workspace dependencies
RUN pnpm install --frozen-lockfile

# Copy source files
COPY apps/auth/ ./apps/auth/
COPY packages/db/ ./packages/db/

# Build @fazri/db (prisma generate + tsc → dist/)
RUN pnpm --filter=@fazri/db build

# Build auth (tsc → dist/)
RUN pnpm --filter=@fazri/auth build

# Create minimal production deployment with only auth's prod deps
RUN pnpm deploy --filter=@fazri/auth --prod --legacy /deploy

FROM node:22-alpine AS runner
WORKDIR /app

# Minimal prod deps + workspace packages (includes @fazri/db with its dist/)
COPY --from=builder /deploy ./

# Compiled auth output
COPY --from=builder /app/apps/auth/dist ./dist

RUN addgroup -g 1001 -S nodejs && \
    adduser -S authuser -u 1001 && \
    chown -R authuser:nodejs /app
USER authuser

EXPOSE 4000
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD node -e "require('http').get('http://localhost:4000/health', (r) => r.statusCode === 200 ? process.exit(0) : process.exit(1))"

CMD ["node", "dist/index.js"]
