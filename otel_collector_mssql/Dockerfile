FROM --platform=linux/amd64 debian:bookworm-slim
RUN apt-get update && apt-get install -y ca-certificates && rm -rf /var/lib/apt/lists/*
ADD https://download.newrelic.com/database-monitoring/nrdot-collector/nrdot-collector-host-linux-amd64-latest.deb /tmp/nrdot.deb
RUN dpkg -i /tmp/nrdot.deb && rm /tmp/nrdot.deb
ENTRYPOINT ["/usr/bin/nrdot-collector-host"]
