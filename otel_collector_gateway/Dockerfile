# relibank-telemetry-gateway: OpenTelemetry Collector (contrib) with the gateway pipeline config baked in.
# Pinned by digest, not by tag (NR-638736). The digest is the multi-arch index of 0.145.0.
FROM otel/opentelemetry-collector-contrib:0.145.0@sha256:a7343f01869071ea3f4c5e1e97df1bb1b3c4d5c77247db80e053a80b9df530c4

# Same as the other collectors here: the license key is baked in at build time (skaffold locally, the image build
# workflow in AKS) and the configs read it as ${env:NEW_RELIC_LICENSE_KEY}. The Deployments set no env for it.
ARG NEW_RELIC_LICENSE_KEY
ENV NEW_RELIC_LICENSE_KEY=$NEW_RELIC_LICENSE_KEY

# In AKS a ConfigMap is mounted over this file (see terraform/aks/app_module/templates/ in catapult-service).
COPY config.yaml /etc/otelcol/config.yaml

# 4317 gRPC and 4318 HTTP (OTLP), 13133 health. Only 4318 is reachable from outside, through the /otlp/ proxy.
EXPOSE 4317 4318 13133

# The base image already has ENTRYPOINT ["/otelcol-contrib"]. The Deployments add a second --config for the
# shared internal telemetry (args replace this CMD).
CMD ["--config=/etc/otelcol/config.yaml"]
