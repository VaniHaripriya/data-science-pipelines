#!/usr/bin/env bash

usage() {
    echo "Usage: $0 [-q] <KUBEFLOW_NS> <APP_NAME> <LOCAL_PORT> <REMOTE_PORT>"
    exit 1
}

QUIET=0
while getopts "q" opt; do
    case $opt in
        q) QUIET=1 ;;
        *) usage ;;
    esac
done
shift $((OPTIND -1))

if [ $# -ne 4 ]; then
    usage
fi

KUBEFLOW_NS=$1
APP_NAME=$2
LOCAL_PORT=$3
REMOTE_PORT=$4

# Debug: Show all pods first
echo "DEBUG: All $APP_NAME pods:"
kubectl get pods -n "$KUBEFLOW_NS" -l "app=$APP_NAME" 
echo "DEBUG: Running $APP_NAME pods only:"
kubectl get pods -n "$KUBEFLOW_NS" -l "app=$APP_NAME" --field-selector=status.phase=Running

POD_NAME=$(kubectl get pods -n "$KUBEFLOW_NS" -l "app=$APP_NAME" --field-selector=status.phase=Running --sort-by='.metadata.creationTimestamp' -o jsonpath='{.items[-1].metadata.name}')
echo "POD_NAME=$POD_NAME"

if [ -z "$POD_NAME" ]; then
    echo "ERROR: No running pods found for app=$APP_NAME in namespace=$KUBEFLOW_NS"
    exit 1
fi

if [ $QUIET -eq 1 ]; then
    kubectl port-forward -n "$KUBEFLOW_NS" "$POD_NAME" "$LOCAL_PORT:$REMOTE_PORT" > /dev/null 2>&1 &
else
    kubectl port-forward -n "$KUBEFLOW_NS" "$POD_NAME" "$LOCAL_PORT:$REMOTE_PORT" &
fi

# wait for the port-forward
sleep 5
