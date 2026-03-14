FROM --platform=linux/amd64 node:20-alpine

# Set working directory
WORKDIR /app

# Copy package files first for Docker layer caching
COPY package.json package-lock.json* ./

# Install dependencies
RUN npm install

# Copy application code
COPY . .

# Expose Vite dev server port
EXPOSE 5173

# Start Vite dev server (accessible from outside container)
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
