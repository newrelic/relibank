# Use the official Microsoft SQL Server 2022 image
FROM mcr.microsoft.com/mssql/server:2022-latest

# Copy the initialization script into the container
COPY init.sql /usr/config/init.sql

# Set environment variables for the database
ENV ACCEPT_EULA=Y
ENV MSSQL_PID=Express

# Expose the default MSSQL port
EXPOSE 1433
