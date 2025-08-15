# Use the official PostgreSQL image
FROM postgres:15

# Set environment variables for the database
ENV POSTGRES_USER=postgres
ENV POSTGRES_PASSWORD=your_password
ENV POSTGRES_DB=accountsdb

# Copy the initialization script to the default location for init scripts
COPY init.sql /docker-entrypoint-initdb.d/
