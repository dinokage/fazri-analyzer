FROM node:22-alpine AS builder
RUN npm install -g pnpm
WORKDIR /app

# Copy everything needed for install + build
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
COPY patches/ ./patches/
COPY apps/auth/ ./apps/auth/
COPY packages/db/ ./packages/db/

# Install all workspace dependencies (patches applied here)
RUN pnpm install --frozen-lockfile

# Patch all samlify instances for ESM named-export interop
RUN node -e " \
  const fs = require('fs'); \
  const { execSync } = require('child_process'); \
  const files = execSync('find node_modules/.pnpm -path \"*/samlify/build/index.js\" 2>/dev/null').toString().trim().split('\n').filter(Boolean); \
  files.forEach(f => { \
    let c = fs.readFileSync(f, 'utf8'); \
    if (!c.includes('exports.default = exports')) { \
      c = c.replace('Object.defineProperty(exports, \"__esModule\", { value: true });', 'Object.defineProperty(exports, \"__esModule\", { value: true });\nexports.default = exports;'); \
      fs.writeFileSync(f, c); \
      console.log('Patched:', f); \
    } \
  }); \
"

# Build @fazri/db (prisma generate + tsc → dist/)
RUN pnpm --filter=@fazri/db build

# Build auth (tsc → dist/)
RUN pnpm --filter=@fazri/auth build

FROM node:22-alpine AS runner
WORKDIR /app

# Copy the full patched node_modules directly (avoids pnpm deploy CAS re-extraction)
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/packages/db ./packages/db

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
