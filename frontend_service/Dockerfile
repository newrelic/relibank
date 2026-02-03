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

ARG NEW_RELIC_ACCOUNT_ID
ENV NEW_RELIC_ACCOUNT_ID=$NEW_RELIC_ACCOUNT_ID

ARG NEW_RELIC_LICENSE_KEY
ENV NEW_RELIC_LICENSE_KEY=$NEW_RELIC_LICENSE_KEY

ARG NEW_RELIC_BROWSER_APPLICATION_ID
ENV NEW_RELIC_BROWSER_APPLICATION_ID=$NEW_RELIC_BROWSER_APPLICATION_ID

ARG NEW_RELIC_TRUST_KEY
ENV NEW_RELIC_TRUST_KEY=$NEW_RELIC_TRUST_KEY

RUN chmod +x generate_nrjs_file.sh
RUN ./generate_nrjs_file.sh

ENV HOST=0.0.0.0
ENV PORT=3000

# Pre-build to optimize Vite dependencies cache
# This prevents the race condition where chunks aren't ready on first page load
RUN npm run build

# Expose the port
EXPOSE 3000

# Set the command to run the development server
CMD ["npm", "run", "dev"]
