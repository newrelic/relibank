# Use the official PostgreSQL 15 image
FROM postgres:15

# Copy the initialization script into the container
COPY init.sql /docker-entrypoint-initdb.d/init.sql

# Expose the default PostgreSQL port
EXPOSE 5432
