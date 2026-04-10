FROM node:22.11.0-alpine AS base
RUN npm install -g pnpm

FROM base AS dependencies
WORKDIR /app
# Copy workspace manifests for reproducible monorepo install
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
COPY apps/web/package.json ./apps/web/
COPY packages/ui/package.json ./packages/ui/
COPY packages/types/package.json ./packages/types/
COPY packages/config/package.json ./packages/config/
RUN pnpm install --frozen-lockfile

FROM base AS build
WORKDIR /app
COPY --from=dependencies /app/node_modules ./node_modules
COPY --from=dependencies /app/apps/web/node_modules ./apps/web/node_modules
COPY . .

# Build-time environment variables (NEXT_PUBLIC_*)
ARG NEXT_PUBLIC_FASTAPI_BASE_URL
ARG NEXT_PUBLIC_CDN_URL
ENV NEXT_PUBLIC_FASTAPI_BASE_URL=$NEXT_PUBLIC_FASTAPI_BASE_URL
ENV NEXT_PUBLIC_CDN_URL=$NEXT_PUBLIC_CDN_URL

ENV NEXT_TELEMETRY_DISABLED=1
RUN pnpm --filter @fazri/web build

FROM base AS runner
WORKDIR /app

ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    HOSTNAME="0.0.0.0"

RUN addgroup --system --gid 1001 nodejs && \
    adduser --system --uid 1001 nextjs

COPY --from=build /app/apps/web/public ./public
RUN mkdir .next && chown nextjs:nodejs .next
COPY --from=build --chown=nextjs:nodejs /app/apps/web/.next/standalone ./
COPY --from=build --chown=nextjs:nodejs /app/apps/web/.next/static ./.next/static

USER nextjs
EXPOSE 3000
ENV PORT=3000

CMD ["node", "server.js"]