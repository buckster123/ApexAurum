# ApexAurum Cloud - Frontend Production Dockerfile
FROM node:20-alpine AS builder

WORKDIR /app

# Install dependencies
COPY package*.json ./
RUN npm install

# Build the app
COPY . .
RUN npm run build

# Production stage - serve static files
FROM node:20-alpine

WORKDIR /app

# Install serve for static hosting
RUN npm install -g serve

# Copy built assets
COPY --from=builder /app/dist ./dist

# Railway provides PORT
ENV PORT=3000
EXPOSE $PORT

# Serve the built app
CMD ["sh", "-c", "serve -s dist -l $PORT"]
