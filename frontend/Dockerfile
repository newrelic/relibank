# Use a Node.js base image
FROM node:24-alpine

# Set the working directory inside the container
WORKDIR /app

# Copy the package.json and package-lock.json files
COPY package*.json ./

# Install project dependencies
RUN npm install

# Copy the rest of your application code
COPY . .

# Expose the port
EXPOSE 3000

RUN npm run build

# Set the command to run the development server
CMD ["npm", "run", "start"]
