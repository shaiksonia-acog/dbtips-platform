# Step 1: Build the React app
FROM node:20.11.1-alpine as build

# Set the working directory
WORKDIR /app

COPY chatbot-component-1.0.3.tgz ./

# Copy the package.json and package-lock.json files to the working directory
COPY package*.json ./

# Install dependencies
RUN npm install

# Copy the rest of the application source code to the working directory
COPY . .

ARG VITE_API_URI
ARG VITE_TARGET_DOSSIER_URI

ENV NODE_OPTIONS="--max-old-space-size=4096"
RUN VITE_API_URI=${VITE_API_URI} VITE_TARGET_DOSSIER_URI=${VITE_TARGET_DOSSIER_URI} npm run build

# Step 2: Serve the app with Nginx
FROM nginx:alpine

# Copy the built files from the previous stage to the Nginx html folder
COPY --from=build /app/dist /usr/share/nginx/html

# Copy a custom Nginx configuration file if necessary
COPY nginx.conf /etc/nginx/nginx.conf
# COPY .htpasswd /etc/apache2/

# Expose port 80
EXPOSE 80

# Start Nginx
CMD ["nginx", "-g", "daemon off;"]


