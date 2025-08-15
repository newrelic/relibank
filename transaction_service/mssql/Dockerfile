# Use the official Microsoft SQL Server image
FROM mcr.microsoft.com/mssql/server:2019-CU18-ubuntu-20.04

# Expose the default MSSQL port
EXPOSE 1433

# Copy the initialization script into the container
# This script will be executed when the container starts
COPY init.sql /usr/config/init.sql

# Set environment variables for the database
ENV ACCEPT_EULA=Y
ENV SA_PASSWORD=YourStrong@Password!
ENV MSSQL_PID=Express
