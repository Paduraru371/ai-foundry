# Development uses the Vite target; the default target is a production nginx image.
FROM node:20-alpine AS deps
WORKDIR /srv
COPY package.json ./
RUN npm install

FROM deps AS dev
COPY . .
EXPOSE 7800
CMD ["npm", "run", "dev"]

FROM deps AS build
COPY . .
RUN npm run build

FROM nginx:1.27-alpine AS prod
COPY --from=build /srv/dist /usr/share/nginx/html
COPY nginx.conf.template /etc/nginx/templates/default.conf.template
ENV API_URL=http://api:7799
EXPOSE 7800
