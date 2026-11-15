# Backend Dockerfile
FROM node:20-alpine AS builder
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build || echo "No build script"

FROM node:20-alpine
WORKDIR /app
COPY --from=builder /app .
EXPOSE 4000
CMD ["node", "src/index.js"]

