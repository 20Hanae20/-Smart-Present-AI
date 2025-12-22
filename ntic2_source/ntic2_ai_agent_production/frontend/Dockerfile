
FROM node:20-alpine AS build
WORKDIR /app

# Install dependencies
COPY package*.json ./
# Install including dev deps so build tools (vite, plugins) are available
RUN npm install --include=dev

# Copy app sources and build
COPY . .
# Print runtime/tool versions to ease debugging
RUN node -v && npm -v
RUN npm run build

FROM nginx:stable-alpine AS production
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
