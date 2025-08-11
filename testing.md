# relibank testing

docker compose up --build
- Sets up containers for bill pay, bill pay consumer, kafka and zookeeper
docker compose up --build --force-recreate

send requests from postman w/ collection

docker compose logs -f bill-pay-consumer
- Use this to view logs if they don't show in docker compose

# rebuild
docker compose down
docker compose up --build

# test individual services
<!-- docker build -t bill-pay-service:latest . -->
<!-- docker run -p 5000:5000 bill-pay-service:latest -->