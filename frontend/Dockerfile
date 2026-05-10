FROM node:20-alpine

WORKDIR /app

# Placeholder: full Vite build added in Phase 3
COPY package*.json ./
RUN npm install --legacy-peer-deps 2>/dev/null || echo "No package.json yet — placeholder container"

EXPOSE 3000

CMD ["sh", "-c", "echo 'Frontend placeholder — Phase 3 implements React app' && tail -f /dev/null"]
