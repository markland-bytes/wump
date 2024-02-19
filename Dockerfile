FROM node:20.10-bookworm-slim

RUN apt-get update && apt-get install -y \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /code

COPY package.json package-lock.json ./
RUN npm install

COPY . .

EXPOSE 3000

CMD [ "npm", "run", "dev" ]

