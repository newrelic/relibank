# Use the official PostgreSQL 15 image
FROM postgres:15

# pg_stat_statements ships in contrib (no install needed) and pg_wait_sampling is in PGDG's
# apt repo (already configured on this base image), but pg_stat_monitor is NOT packaged by
# PGDG for apt/deb at all (only its yum/RPM repo) — needs Percona's own apt repo instead.
# All three are needed for New Relic's nri-postgresql query/wait-time monitoring
# (PostgresWaitEvents needs pg_wait_sampling, PostgresIndividualQueries/execution plans need
# pg_stat_monitor).
RUN apt-get update && apt-get install -y \
      curl \
      gnupg \
      lsb-release \
      postgresql-15-pg-wait-sampling \
    && curl -o /tmp/percona-release.deb https://repo.percona.com/apt/percona-release_latest.generic_all.deb \
    && apt-get install -y /tmp/percona-release.deb \
    && percona-release setup ppg-15 \
    && apt-get update && apt-get install -y percona-pg-stat-monitor15 \
    && rm -f /tmp/percona-release.deb \
    && rm -rf /var/lib/apt/lists/*

# Copy the initialization script into the container
COPY init.sql /docker-entrypoint-initdb.d/init.sql

# Expose the default PostgreSQL port
EXPOSE 5432
