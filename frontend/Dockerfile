FROM node:20-alpine

WORKDIR /workspace

# Dependencies
COPY package.json package-lock.json* ./
RUN npm install --registry=https://registry.npmmirror.com

# Copy source
COPY . .

# Expose port
EXPOSE 3000

# Run dev server
CMD ["npm", "run", "dev"]
