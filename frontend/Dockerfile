
FROM node:20-alpine

# Set the working directory inside the container
WORKDIR /app

# Copy the package files first (this leverages Docker cache for faster rebuilds)
COPY package.json package-lock.json* ./

# Install dependencies
RUN npm install

# Copy the rest of your Next.js app source code
COPY . .

# Build the Next.js app for production
RUN npm run build

# Expose the web port
EXPOSE 3000

# Start the Next.js production server
CMD ["npm", "run", "start"]