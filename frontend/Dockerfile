FROM node:22-alpine

WORKDIR /app

COPY package*.json ./

RUN npm install

COPY . .

EXPOSE 4200

# Set host to 0.0.0.0 so it is accessible from outside the container
CMD ["npm", "run", "start", "--", "--host", "0.0.0.0", "--poll", "1000"]
