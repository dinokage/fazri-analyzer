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

# Generate Prisma client and build auth
RUN pnpm --filter=@fazri/db db:generate
RUN pnpm --filter=@fazri/auth build

FROM node:22-alpine AS runner
RUN npm install -g pnpm
WORKDIR /app

COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
COPY apps/auth/package.json ./apps/auth/
COPY packages/db/package.json ./packages/db/

RUN pnpm install --frozen-lockfile --prod

COPY --from=builder /app/apps/auth/dist ./apps/auth/dist
COPY --from=builder /app/node_modules/.prisma ./node_modules/.prisma

RUN addgroup -g 1001 -S nodejs && \
    adduser -S authuser -u 1001 && \
    chown -R authuser:nodejs /app
USER authuser

EXPOSE 4000
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD node -e "require('http').get('http://localhost:4000/health', (r) => r.statusCode === 200 ? process.exit(0) : process.exit(1))"

CMD ["node", "apps/auth/dist/index.js"]
