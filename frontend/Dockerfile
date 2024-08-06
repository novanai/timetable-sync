FROM node:22.5.1-alpine

WORKDIR /app

COPY frontend/package.json .
COPY frontend/package-lock.json .

RUN npm install

COPY frontend .

RUN npm run build

CMD ["node", "build"]
