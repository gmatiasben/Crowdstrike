curl -O https://raw.githubusercontent.com/pbaumbach2/falcon-k8s-cluster-deploy/main/falcon-k8s-cluster-deploy.sh
chmod +x falcon-k8s-cluster-deploy.sh
  
export FALCON_CLIENT_ID=xxxxxxxx
export FALCON_CLIENT_SECRET=xxxxxxx
export FALCON_CLOUD=us-1|us-2
export CLUSTER_NAME="$(kubectl config view --minify -o jsonpath='{.contexts[].context.cluster}')"
 
./falcon-k8s-cluster-deploy.sh \
  --client-id "$FALCON_CLIENT_ID" \
  --client-secret "$FALCON_CLIENT_SECRET" \
  --cluster "$CLUSTER_NAME" \
  --region "$FALCON_CLOUD " \
  --tags "pov-falcon" \
  --ebpf "true
