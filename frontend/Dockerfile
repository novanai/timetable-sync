FROM node:23.11-slim

WORKDIR /app

COPY frontend/package.json .
COPY frontend/package-lock.json .

RUN npm install

COPY frontend .

RUN npm run build

CMD node build
