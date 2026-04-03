# relibank testing

skaffold dev
- Builds all service images and deploys the full stack to Kubernetes with port forwarding

# rebuild / reset

skaffold delete
- Tears down all Kubernetes resources (note: persistent volumes may need manual cleanup)

kubectl delete pvc --all -n relibank
- Destroys persistent data (databases). Run this if you need a clean slate.

skaffold dev
- Redeploy after cleanup

# send requests

Send requests from Postman with collection
