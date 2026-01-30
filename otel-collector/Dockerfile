# Multi-stage build for OpenTelemetry Collector with Java support for JMX receiver
# This image bundles the OTEL Collector with Java 17 runtime and JMX scraper JAR

FROM alpine:latest as prep

# OpenTelemetry Collector Binary
ARG OTEL_VERSION=0.144.0
ARG TARGETARCH=linux_amd64
ADD "https://github.com/open-telemetry/opentelemetry-collector-releases/releases/download/v${OTEL_VERSION}/otelcol-contrib_${OTEL_VERSION}_${TARGETARCH}.tar.gz" /otelcontribcol
RUN tar -zxvf /otelcontribcol

# JMX Scraper JAR (for JMX receiver with YAML-based configuration)
ARG JMX_SCRAPER_JAR_VERSION=1.52.0
ADD https://github.com/open-telemetry/opentelemetry-java-contrib/releases/download/v${JMX_SCRAPER_JAR_VERSION}/opentelemetry-jmx-scraper.jar /opt/opentelemetry-jmx-scraper.jar

# Set permissions for nonroot user (uid 65532)
ARG USER_UID=65532
RUN chown ${USER_UID} /opt/opentelemetry-jmx-scraper.jar

# Final minimal image with Java runtime
FROM amazoncorretto:17-alpine

COPY --from=prep /opt/opentelemetry-jmx-scraper.jar /opt/opentelemetry-jmx-scraper.jar
COPY --from=prep /otelcol-contrib /otelcol-contrib

EXPOSE 4317 4318 8888 13133
ENTRYPOINT ["/otelcol-contrib"]
CMD ["--config", "/etc/otel/config.yaml"]
