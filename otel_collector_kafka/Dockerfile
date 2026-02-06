# Multi-stage build for OpenTelemetry Collector with Java support for JMX receiver
# Using Amazon Corretto for better cross-platform compatibility
# This image bundles the OTEL Collector with Java 17 runtime and JMX scraper JAR
# Automatically detects architecture: arm64 for Apple Silicon, amd64 for production

FROM alpine:latest as prep

# OpenTelemetry Collector Binary
ARG OTEL_VERSION=0.145.0
ARG TARGETARCH
# Docker automatically sets TARGETARCH to the build platform (arm64 or amd64)
ADD "https://github.com/open-telemetry/opentelemetry-collector-releases/releases/download/v${OTEL_VERSION}/otelcol-contrib_${OTEL_VERSION}_linux_${TARGETARCH}.tar.gz" /otelcontribcol
RUN tar -zxvf /otelcontribcol

# JMX Scraper JAR (for JMX receiver with YAML-based configuration)
ARG JMX_SCRAPER_JAR_VERSION=1.52.0
ADD https://github.com/open-telemetry/opentelemetry-java-contrib/releases/download/v${JMX_SCRAPER_JAR_VERSION}/opentelemetry-jmx-scraper.jar /opt/opentelemetry-jmx-scraper.jar

# Set permissions for nonroot user (uid 65532)
ARG USER_UID=65532
RUN chown ${USER_UID} /opt/opentelemetry-jmx-scraper.jar

# Final minimal image with Java runtime - Eclipse Temurin (official OpenJDK successor)
# Supports multi-arch: arm64 (Apple Silicon) and amd64
FROM eclipse-temurin:17-jre

COPY --from=prep /opt/opentelemetry-jmx-scraper.jar /opt/opentelemetry-jmx-scraper.jar
COPY --from=prep /otelcol-contrib /otelcol-contrib

EXPOSE 4317 4318 8888 13133
ENTRYPOINT ["/otelcol-contrib"]
CMD ["--config", "/conf/otel-agent-config.yaml"]
