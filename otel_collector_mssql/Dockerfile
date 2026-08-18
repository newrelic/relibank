FROM --platform=linux/amd64 debian:bookworm-slim
RUN apt-get update && apt-get install -y ca-certificates curl && rm -rf /var/lib/apt/lists/*
RUN NRDOT_VERSION=$(curl -s https://api.github.com/repos/newrelic/nrdot-collector-releases/releases/latest | grep '"tag_name":' | awk -F'"' '{print $4}') && \
    curl -L "https://github.com/newrelic/nrdot-collector-releases/releases/download/${NRDOT_VERSION}/nrdot-collector_${NRDOT_VERSION}_linux_amd64.deb" --output /tmp/nrdot-collector.deb && \
    dpkg -i /tmp/nrdot-collector.deb && rm /tmp/nrdot-collector.deb
ENTRYPOINT ["/usr/bin/nrdot-collector"]
