# Copy all files to VM

./install_docker.sh


docker build -t fastapi-app .


# Run app and redis
docker compose up --build


docker run -d -p 8000:8000 --name fastapi fastapi-app -d


# Shutdown
docker compose down



# Run commands in redis
docker exec -it <redis-container> redis-cli


# Redis update for publishing service status
SET profile_service_status up
PUBLISH profile_service_status_updates up
