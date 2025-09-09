# relibank

---

### ⚙️ Test connection to New Relic

1. Connect to the service's container, docker example `docker exec -it bill-pay /bin/sh`

2. newrelic-admin validate-config LOCATION_OF_NEWRELIC.INI

3. If needed, add a logfile to newrelic.ini
```[newrelic]
log_file = /app/newrelic.log
log_level = info
```

4. Validate logs with ```docker exec -it bill-pay cat newrelic-agent.log```

---

### ⚙️ Formatting

1. ```ruff format``` https://docs.astral.sh/ruff/formatter/#ruff-format 
