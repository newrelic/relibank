#!/bin/bash

# ===========================================
# RELIBANK CONFIGURATION MANAGER
# Central place to manage all secrets and variables
# ===========================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🔧 Relibank Configuration Manager${NC}"
echo "=================================="

# ===========================================
# CONFIGURATION VARIABLES
# Edit these values to update your deployment
# ===========================================

# ========== DATABASE CONFIGURATION ==========
POSTGRES_PASSWORD="your_password"
MSSQL_SA_PASSWORD="YourStrong@Password!"

# ========== AZURE SERVICES ==========
AZURE_ACS_CONNECTION_STRING=""  # Add your Azure Communication Services connection string
AZURE_ACS_EMAIL_ENDPOINT="https://your-acs-resource-name.communication.azure.com"
AZURE_ACS_SMS_PHONE_NUMBER="+15551234567"

# ========== OPTIONAL THIRD-PARTY SERVICES ==========
# Uncomment and set these if you want to use them
# TWILIO_ACCOUNT_SID=""
# TWILIO_AUTH_TOKEN=""
# TWILIO_PHONE_NUMBER=""
# SENDGRID_API_KEY=""
# SENDGRID_SENDER_EMAIL=""

# ========== ENVIRONMENT SETTINGS ==========
ENVIRONMENT="local"  # Options: local, dev, staging, production
LOG_LEVEL="INFO"     # Options: DEBUG, INFO, WARNING, ERROR
DEBUG_MODE="false"   # Options: true, false

# ===========================================
# FUNCTIONS
# ===========================================

base64_encode() {
    echo -n "$1" | base64
}

update_configmap() {
    echo -e "${YELLOW}📝 Updating ConfigMap...${NC}"

    # Update environment-specific values in ConfigMap
    kubectl patch configmap relibank-config -n relibank --type merge -p "{
        \"data\": {
            \"ENVIRONMENT\": \"$ENVIRONMENT\",
            \"LOG_LEVEL\": \"$LOG_LEVEL\",
            \"DEBUG\": \"$DEBUG_MODE\",
            \"AZURE_ACS_EMAIL_ENDPOINT\": \"$AZURE_ACS_EMAIL_ENDPOINT\",
            \"AZURE_ACS_SMS_PHONE_NUMBER\": \"$AZURE_ACS_SMS_PHONE_NUMBER\"
        }
    }"
}

update_secrets() {
    echo -e "${YELLOW}🔐 Updating Secrets...${NC}"

    # Encode passwords
    DB_PASSWORD_B64=$(base64_encode "$POSTGRES_PASSWORD")
    SA_PASSWORD_B64=$(base64_encode "$MSSQL_SA_PASSWORD")
    AZURE_ACS_B64=$(base64_encode "$AZURE_ACS_CONNECTION_STRING")

    # Update main secrets
    kubectl patch secret relibank-secrets -n relibank --type merge -p "{
        \"data\": {
            \"DB_PASSWORD\": \"$DB_PASSWORD_B64\",
            \"SA_PASSWORD\": \"$SA_PASSWORD_B64\",
            \"AZURE_ACS_CONNECTION_STRING\": \"$AZURE_ACS_B64\"
        }
    }"

    # Update environment-specific secrets
    kubectl patch secret relibank-secrets-env -n relibank --type merge -p "{
        \"stringData\": {
            \"ENVIRONMENT_OVERRIDE\": \"$ENVIRONMENT-deployment\"
        }
    }"
}

restart_deployments() {
    echo -e "${YELLOW}🔄 Restarting deployments to pick up new configuration...${NC}"

    kubectl rollout restart deployment/accounts-service -n relibank
    kubectl rollout restart deployment/transaction-service -n relibank
    kubectl rollout restart deployment/bill-pay-service -n relibank
    kubectl rollout restart deployment/notifications-service -n relibank
    kubectl rollout restart deployment/scheduler-service -n relibank

    echo -e "${GREEN}✅ All deployments restarted${NC}"
}

show_current_config() {
    echo -e "${BLUE}📊 Current Configuration:${NC}"
    echo "========================"
    echo "Environment: $ENVIRONMENT"
    echo "Log Level: $LOG_LEVEL"
    echo "Debug Mode: $DEBUG_MODE"
    echo "Azure ACS Endpoint: $AZURE_ACS_EMAIL_ENDPOINT"
    echo "Azure ACS Phone: $AZURE_ACS_SMS_PHONE_NUMBER"
    echo ""
    echo -e "${YELLOW}🔐 Secrets (masked):${NC}"
    echo "PostgreSQL Password: ${POSTGRES_PASSWORD:0:3}***"
    echo "MSSQL SA Password: ${MSSQL_SA_PASSWORD:0:3}***"
    if [ -n "$AZURE_ACS_CONNECTION_STRING" ]; then
        echo "Azure ACS Connection: ${AZURE_ACS_CONNECTION_STRING:0:10}***"
    else
        echo "Azure ACS Connection: Not set"
    fi
}

validate_config() {
    echo -e "${YELLOW}✅ Validating configuration...${NC}"

    # Check if namespace exists
    if ! kubectl get namespace relibank &> /dev/null; then
        echo -e "${RED}❌ Namespace 'relibank' does not exist. Run deploy-k8s.sh first.${NC}"
        exit 1
    fi

    # Check if ConfigMap exists
    if ! kubectl get configmap relibank-config -n relibank &> /dev/null; then
        echo -e "${RED}❌ ConfigMap 'relibank-config' does not exist. Run deploy-k8s.sh first.${NC}"
        exit 1
    fi

    # Check if Secrets exist
    if ! kubectl get secret relibank-secrets -n relibank &> /dev/null; then
        echo -e "${RED}❌ Secret 'relibank-secrets' does not exist. Run deploy-k8s.sh first.${NC}"
        exit 1
    fi

    echo -e "${GREEN}✅ All required resources exist${NC}"
}

# ===========================================
# MAIN SCRIPT
# ===========================================

case "${1:-}" in
    "show")
        show_current_config
        ;;
    "update")
        validate_config
        show_current_config
        echo ""
        read -p "Do you want to apply these changes? (y/N): " -r
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            update_configmap
            update_secrets
            restart_deployments
            echo -e "${GREEN}🎉 Configuration updated successfully!${NC}"
        else
            echo "Configuration update cancelled."
        fi
        ;;
    "restart")
        validate_config
        restart_deployments
        ;;
    *)
        echo "Usage: $0 [show|update|restart]"
        echo ""
        echo "Commands:"
        echo "  show    - Display current configuration"
        echo "  update  - Update configuration and restart services"
        echo "  restart - Restart all services to pick up config changes"
        echo ""
        echo "To modify configuration, edit the variables at the top of this script."
        exit 1
        ;;
esac
