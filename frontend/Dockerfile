# Dev-server image for the React frontend. Mirrors how start.sh runs it natively
# (`npm run dev`), but inside a container so users never install Node.
FROM node:20-slim

WORKDIR /app/frontend

# Install deps first for layer caching (package-lock.json is optional via the glob)
COPY package*.json ./
RUN npm install

# Copy the rest of the app (node_modules excluded by .dockerignore)
COPY . .

EXPOSE 5173

# --host binds 0.0.0.0 so the dev server is reachable from the host browser.
# Without it, Vite binds localhost INSIDE the container and :5173 is unreachable.
CMD ["npm", "run", "dev", "--", "--host", "--port", "5173"]
