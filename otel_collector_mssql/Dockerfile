FROM --platform=linux/amd64 debian:bookworm-slim

# Install CA certificates for TLS connections
RUN apt-get update && apt-get install -y ca-certificates && rm -rf /var/lib/apt/lists/*

# Download nrdot-collector binary
ADD https://download.newrelic.com/database-monitoring/nrdot-collector/mssql/nrdot-collector-host-linux-amd64-1.0.0 /usr/local/bin/otelcol

# Set permissions and make executable
RUN chmod +x /usr/local/bin/otelcol

ENTRYPOINT ["/usr/local/bin/otelcol"]
