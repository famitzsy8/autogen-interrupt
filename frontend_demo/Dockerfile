# Node.js container for frontend_demo Next.js app with dependencies
FROM node:18-slim

WORKDIR /app

# Copy package files first for better layer caching
COPY package*.json ./

# Install dependencies
RUN npm install

# Copy application code
COPY . .

# Expose the Next.js development server port
EXPOSE 3000

# Keep container running for VSCode attachment
CMD ["tail", "-f", "/dev/null"]