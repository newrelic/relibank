# Shared build: build-push-images.yml builds this same Dockerfile for every environment,
# including `events` (deployed via k8s/base kustomize, not this Terraform module). If
# `events` is ever rebuilt off `main` (force_rebuild, cache miss, etc.), its still-old
# `k8s/base/infrastructure/nrdot-collector-mssql-deployment.yaml` command
# (`nrdot-collector-host`) will crash-loop against this binary (`nrdot-collector`) —
# same failure app_module hit before its command field was updated to match. Known,
# accepted gap as of 2026-08-18; fix is porting db360-new-image-rebased's k8s/base
# changes to main properly, not patching around it here.
FROM --platform=linux/amd64 debian:bookworm-slim
RUN apt-get update && apt-get install -y ca-certificates curl && rm -rf /var/lib/apt/lists/*
RUN NRDOT_VERSION=$(curl -s https://api.github.com/repos/newrelic/nrdot-collector-releases/releases/latest | grep '"tag_name":' | awk -F'"' '{print $4}') && \
    curl -L "https://github.com/newrelic/nrdot-collector-releases/releases/download/${NRDOT_VERSION}/nrdot-collector_${NRDOT_VERSION}_linux_amd64.deb" --output /tmp/nrdot-collector.deb && \
    dpkg -i /tmp/nrdot-collector.deb && rm /tmp/nrdot-collector.deb
ENTRYPOINT ["/usr/bin/nrdot-collector"]
