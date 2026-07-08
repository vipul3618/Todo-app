# Flask Todo App

A simple **Flask-based Todo Application** containerized using **Docker** and **Docker Compose** with a **MySQL** backend.

## Features

* User Registration & Login
* Add, Edit & Delete Tasks
* Mark Tasks as Completed
* MySQL Database
* Dockerized Deployment

## Tech Stack

* Python 3.11
* Flask
* MySQL 8.0
* Docker
* Docker Compose

## Run the Application

1. Clone the repository.

2. Create a `.env` file from `.env.example`.

3. Build and start the application:

```bash
docker compose up --build
```

4. Open your browser:

```text
http://localhost:5000 or http://<public_ip>:5000
```

## Stop the Application

```bash
docker compose down
```

## Note

This project is created for learning Docker containerization and DevOps deployment practices.
