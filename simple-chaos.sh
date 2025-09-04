#!/bin/bash

# Simple chaos engineering scripts for Relibank
# No Python controller needed - just Docker commands

SERVICES=("accounts-service" "transaction-service" "bill-pay-service" "notifications-service" "kafka" "accounts-db" "mssql")

kill_random_service() {
    local service=${SERVICES[$RANDOM % ${#SERVICES[@]}]}
    echo "🔥 Killing $service"
    docker kill $service
}

restart_random_service() {
    local service=${SERVICES[$RANDOM % ${#SERVICES[@]}]}
    echo "🔄 Restarting $service"
    docker restart $service
}

pause_service() {
    local service=${1:-${SERVICES[$RANDOM % ${#SERVICES[@]}]}}
    local duration=${2:-30}
    echo "⏸️  Pausing $service for ${duration}s"
    docker pause $service
    sleep $duration
    docker unpause $service
    echo "▶️  Resumed $service"
}

stress_test() {
    local service=${1:-"transaction-service"}
    echo "💪 Running CPU stress on $service"
    docker exec $service stress-ng --cpu 2 --timeout 60s &
}

case "${1:-}" in
    "kill") kill_random_service ;;
    "restart") restart_random_service ;;
    "pause") pause_service $2 $3 ;;
    "stress") stress_test $2 ;;
    *)
        echo "Usage: $0 {kill|restart|pause [service] [duration]|stress [service]}"
        echo "Available services: ${SERVICES[*]}"
        ;;
esac
