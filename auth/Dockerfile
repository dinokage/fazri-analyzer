FROM node:22-alpine AS builder
RUN npm install -g pnpm
WORKDIR /app
COPY package.json ./
RUN pnpm install --no-frozen-lockfile
COPY . .
RUN pnpm run build

FROM node:22-alpine AS runner
RUN npm install -g pnpm
WORKDIR /app
COPY package.json ./
COPY --from=builder /app/node_modules ./node_modules
RUN pnpm prune --prod
COPY --from=builder /app/dist ./dist
COPY prisma ./prisma

RUN addgroup -g 1001 -S nodejs && \
    adduser -S authuser -u 1001 && \
    chown -R authuser:nodejs /app
USER authuser

EXPOSE 4000
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD node -e "require('http').get('http://localhost:4000/health', (r) => r.statusCode === 200 ? process.exit(0) : process.exit(1))"

CMD ["node", "dist/index.js"]
