# S2 "Data processing and Storage" Project
## Useful links
1. yourDomain/admin - Django admin panel
2. yourDomain/swagger - Swagger
   
## How to Deploy? 

1. Clone repo using Git
```
git clone https://github.com/Nikita-NN/SimpleBanking-backend.git
```
```
cd SimpleBanking-backend
```
2. Install Docker and Docker compose plugin
3. Set up db using docker-compose.yml file
```
services:
  db:
    image: postgres:13
    volumes:
      - postgres_data:/var/lib/postgresql/data
    environment:
      POSTGRES_DB: new_db
      POSTGRES_USER: userdb
      POSTGRES_PASSWORD: securepassword123

  web:
    build: .
    command: python manage.py runserver 0.0.0.0:8000
    volumes:
      - .:/usr/src/app
    ports:
      - "8080:8000"
    depends_on:
      - db
    environment:
      POSTGRES_DB: postgres
      POSTGRES_USER: ""
      POSTGRES_PASSWORD: ""
      DB_HOST: db
      DB_PORT: 5432
```
5. Use
```
docker compose up --build
```
6. To access admin panel use
```
docker exec -it containerId python3 manage.py createsuperuser
```
7. To generate random data use
```
docker ps
```

```
docker exec -it containerId python3 seed.py
```
