FROM node:20-alpine

RUN apk add --no-cache tzdata
ENV TZ=Asia/Ho_Chi_Minh

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
