# Azure OpenAI Configuration for Chatbot Service

## Overview

The chatbot service Azure OpenAI configuration is managed through Kustomize generators that use environment variables. This prevents hardcoding sensitive credentials in git.

## How It Works

### Environment Variables Required

These must be set before running `skaffold` or `kubectl apply`:

```bash
export AZURE_OPENAI_ENDPOINT="https://eastus.api.cognitive.microsoft.com/"
export AZURE_OPENAI_API_KEY="<your-api-key>"
export ASSISTANT_A_ID="<your-assistant-a-id>"
export ASSISTANT_B_ID="<your-assistant-b-id>"
export ASSISTANT_B_DELAY_SECONDS="0"
```

### Kustomize Configuration

Both `dev` and `azure-prod` overlays use `configMapGenerator` and `secretGenerator` to create resources from environment variables:

```yaml
configMapGenerator:
  - name: azure-assistant-config
    namespace: relibank
    literals:
      - assistant-a-id=${ASSISTANT_A_ID}
      - assistant-b-id=${ASSISTANT_B_ID}
    behavior: replace

secretGenerator:
  - name: azure-openai-secrets
    namespace: relibank
    literals:
      - endpoint=${AZURE_OPENAI_ENDPOINT}
      - api-key=${AZURE_OPENAI_API_KEY}
    type: Opaque
    behavior: replace
```

### Generated Resources

This creates two Kubernetes resources:

1. **ConfigMap**: `azure-assistant-config`
   - `assistant-a-id`: Azure OpenAI Assistant A ID
   - `assistant-b-id`: Azure OpenAI Assistant B ID

2. **Secret**: `azure-openai-secrets`
   - `endpoint`: Azure OpenAI API endpoint
   - `api-key`: Azure OpenAI API key

## Usage

### Local Development (dev overlay)

```bash
# Source environment variables from skaffold.env
source skaffold.env

# Deploy with Skaffold
skaffold dev
# or
skaffold run
```

Skaffold automatically loads environment variables from `skaffold.env` and Kustomize uses them to generate the ConfigMap and Secret.

### Production (azure-prod overlay)

#### Option 1: Using GitHub Actions

The workflow at `.github/workflows/build-push-images.yml` sets environment variables from GitHub secrets:

```yaml
- name: Create skaffold.env file
  run: |
    cat > skaffold.env << EOF
    AZURE_OPENAI_ENDPOINT=${{ secrets.AZURE_OPENAI_ENDPOINT }}
    AZURE_OPENAI_API_KEY=${{ secrets.AZURE_OPENAI_API_KEY }}
    ASSISTANT_A_ID=${{ secrets.ASSISTANT_A_ID }}
    ASSISTANT_B_ID=${{ secrets.ASSISTANT_B_ID }}
    ASSISTANT_B_DELAY_SECONDS=${{ vars.ASSISTANT_B_DELAY_SECONDS }}
    EOF
```

**Required GitHub Secrets:**
- `AZURE_OPENAI_ENDPOINT`
- `AZURE_OPENAI_API_KEY`
- `ASSISTANT_A_ID`
- `ASSISTANT_B_ID`

**Required GitHub Variables:**
- `ASSISTANT_B_DELAY_SECONDS`

#### Option 2: Manual Deployment

```bash
# Set environment variables
export AZURE_OPENAI_ENDPOINT="https://eastus.api.cognitive.microsoft.com/"
export AZURE_OPENAI_API_KEY="your-key-here"
export ASSISTANT_A_ID="asst_xxx"
export ASSISTANT_B_ID="asst_yyy"

# Apply with Kustomize
kubectl apply -k k8s/overlays/azure-prod
```

## Security Notes

1. **Never commit** actual credentials to git
2. **skaffold.env** should be in `.gitignore` (contains local dev credentials)
3. **Production** credentials should come from:
   - GitHub Secrets (for CI/CD)
   - Azure Key Vault (for runtime)
   - Kubernetes External Secrets Operator (alternative)

## Troubleshooting

### ConfigMap/Secret not created

If resources aren't created, check:

1. **Environment variables are set:**
   ```bash
   echo $AZURE_OPENAI_ENDPOINT
   echo $AZURE_OPENAI_API_KEY
   ```

2. **Kustomize can access them:**
   ```bash
   kustomize build k8s/overlays/dev | grep -A 5 "azure-assistant-config"
   ```

3. **Run kubectl apply with --server-dry-run to see what would be created:**
   ```bash
   kubectl apply -k k8s/overlays/dev --dry-run=server
   ```

### Values not substituted

If you see `${AZURE_OPENAI_ENDPOINT}` literals in the deployed resources:

- Kustomize substitution requires `envsubst` or enabling the feature
- Alternative: Use `kubectl create` with `--from-literal` flags
- Or use Helm instead of Kustomize

### Manual Creation (workaround)

If generators don't work, manually create resources:

```bash
kubectl create configmap azure-assistant-config -n relibank \
  --from-literal=assistant-a-id="${ASSISTANT_A_ID}" \
  --from-literal=assistant-b-id="${ASSISTANT_B_ID}" \
  --dry-run=client -o yaml | kubectl apply -f -

kubectl create secret generic azure-openai-secrets -n relibank \
  --from-literal=endpoint="${AZURE_OPENAI_ENDPOINT}" \
  --from-literal=api-key="${AZURE_OPENAI_API_KEY}" \
  --dry-run=client -o yaml | kubectl apply -f -
```

## Migration from Hardcoded Values

Previous configuration files had hardcoded values:

```yaml
# OLD (removed)
data:
  assistant-a-id: "asst_kCFt9Bl38P4MsDac3ExgvlzK"  # ❌ Hardcoded
```

Now replaced with generators:

```yaml
# NEW (current)
configMapGenerator:
  - name: azure-assistant-config
    literals:
      - assistant-a-id=${ASSISTANT_A_ID}  # ✅ From env var
```

## Files Changed

- ❌ **Removed**: `k8s/overlays/dev/chatbot-azure-config.yaml` (had hardcoded values)
- ❌ **Removed**: `k8s/overlays/azure-prod/chatbot-azure-config.yaml` (had hardcoded values)
- ✅ **Updated**: `k8s/overlays/dev/kustomization.yaml` (added generators)
- ✅ **Updated**: `k8s/overlays/azure-prod/kustomization.yaml` (added generators)
- ✅ **Updated**: `.github/workflows/build-push-images.yml` (added Azure OpenAI env vars)
