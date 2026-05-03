# Canary Deployment Pipeline on Azure DevOps + AKS

[![Azure DevOps](https://img.shields.io/badge/Azure_DevOps-Pipeline-blue)](https://dev.azure.com)
[![AKS](https://img.shields.io/badge/AKS-Kubernetes-326CE5)](https://azure.microsoft.com/en-us/products/kubernetes-service)
[![ACR](https://img.shields.io/badge/ACR-Container_Registry-0078D4)](https://azure.microsoft.com/en-us/products/container-registry)
[![Docker](https://img.shields.io/badge/Docker-linux%2Famd64-blue)](https://docker.com)
[![Status](https://img.shields.io/badge/Pipeline-PASSING-brightgreen)]()

---

## Overview

This project implements a canary deployment pipeline on Azure DevOps that automatically routes 10% of live traffic to a new release while keeping 90% on the stable version. If the canary passes a health check after 2 minutes, it is promoted to stable. If it fails, the pipeline rolls back automatically - no manual intervention required.

The entire setup runs on a single-node AKS cluster using Azure Container Registry for image storage and Azure DevOps Pipelines for CI/CD automation. Every push to `main` triggers the full pipeline.

---

## Why Canary?

Canary sits between rolling updates and blue/green in terms of cost and safety. A rolling update replaces pods gradually with no traffic control. Blue/green gives full isolation but doubles infrastructure cost. Canary gives a real traffic signal - a small percentage of live users hit the new version - without provisioning an entirely separate environment. For a production service where silent regressions matter more than hard failures, canary is the right trade-off.

---

## Architecture

### AKS Cluster (Standard_B2s_v2) - Central India

Single-node Kubernetes cluster running all workloads:

- **app-stable** - 9 replicas running `flask-app:stable` (90% of traffic)
- **app-canary** - 1 replica running `flask-app:canary` (10% of traffic)
- **flask-service** - LoadBalancer service selecting pods by `app: flask-app` label, routing across all 10 pods

The traffic split requires no service mesh or ingress controller. One Kubernetes Service selects all pods with the shared label. With 9 stable and 1 canary replica behind a single service, the load balancer distributes requests proportionally.


### ACR (lakshyaacr)

Stores `flask-app:stable` and `flask-app:canary` image tags. AKS pulls images using a Kubernetes `imagePullSecret` backed by ACR admin credentials.

<img width="2457" height="1708" alt="image" src="https://github.com/user-attachments/assets/25f7d055-191f-4e84-9181-4e52f29898ef" />
<p align="center"><strong>Architecture Diagram </strong></p>

---

## Project Structure

```
canary-app/
│
├── app.py                      # Flask app returning version and message
├── Dockerfile                  # Container definition (linux/amd64)
├── azure-pipelines.yml         # Pipeline: Build → DeployCanary → HealthCheck → Promote
└── k8s/
    ├── stable-deployment.yaml  # 9 replicas - stable version (90% traffic)
    ├── canary-deployment.yaml  # 1 replica - canary version (10% traffic)
    └── service.yaml            # LoadBalancer routing to both deployments
```

---

## Pipeline Stages

Pipeline defined in `azure-pipelines.yml` with four stages:

```yaml
stages:
  - Build
  - DeployCanary
  - HealthCheck
  - Promote
```

<img width="1148" height="649" alt="all 4 stages green" src="https://github.com/user-attachments/assets/94a82023-3f42-48d0-8b10-20f54cd43042" />

<p align="center"><strong>Azure DevOps pipeline - all 4 stages passing: Build → DeployCanary → HealthCheck → Promote.</strong></p>


---

### Build

Builds the Docker image for `linux/amd64` and pushes to ACR as `flask-app:canary`.

```bash
docker buildx build --platform linux/amd64 \
  -t lakshyaacr.azurecr.io/flask-app:canary \
  --push .
```

> The `--platform` flag is required. The AKS node runs AMD64 but the dev machine is ARM64 (Apple Silicon). Without it, the image silently fails to run on the cluster.

---

### Deploy Canary (10% traffic)

Applies `canary-deployment.yaml` to AKS, bringing 1 new pod live alongside the 9 stable pods. The shared LoadBalancer service begins routing ~10% of incoming requests to the canary immediately.

```yaml
- task: KubernetesManifest@1
  inputs:
    action: deploy
    kubernetesServiceConnection: aks-connection
    manifests: k8s/canary-deployment.yaml
```

<img width="508" height="173" alt="kubectl get pods" src="https://github.com/user-attachments/assets/5aaf93e3-c4a8-4a36-9821-85d2b9d83bed" />

<p align="center"><strong>AKS cluster - 9 stable pods and 1 canary pod all Running.</strong></p>



---

### Health Check

Waits 2 minutes for the deployment to stabilize, then checks rollout status:

```bash
sleep 120
kubectl rollout status deployment/app-canary --timeout=60s
```

If the canary is healthy, the pipeline proceeds to Promote. If not, it fails here - the canary is rolled back and stable pods continue serving 100% of traffic unaffected.

---

### Promote

Only runs if HealthCheck passes. Rebuilds the image tagged as `flask-app:stable` and applies `stable-deployment.yaml`, replacing the previous stable version with the promoted canary build.

---

## Traffic Split

The 90/10 split is achieved without a service mesh. One Kubernetes Service selects all pods with label `app: flask-app`. With 9 stable replicas and 1 canary replica, the load balancer distributes traffic proportionally.

Verified by hitting the endpoint 20 times and observing the version distribution:

```bash
for i in {1..20}; do curl -s http://<EXTERNAL_IP>/ ; echo; done
```

<img width="786" height="513" alt="curl output" src="https://github.com/user-attachments/assets/35bfaee8-ed00-4665-8b9f-f71dc18bfd81" />

<p align="center"><strong>~1-in-10 responses served by the canary pod, confirming pod-level load distribution.</strong></p>



The live app responding from both versions:

<img width="1458" height="924" alt="browser v1" src="https://github.com/user-attachments/assets/f7aa6d5a-ec3f-4aa8-8a63-698e0bca0f94" />
<img width="1460" height="910" alt="browser v2" src="https://github.com/user-attachments/assets/3b8c8a26-4c45-403a-b36f-04795ce88832" />

<p align="center"><strong>v1 (stable) and v2 (canary) both serving live traffic from the AKS LoadBalancer.
</strong></p>

---

## Azure Monitor Alerting

Pod count alert configured on `canary-aks`. Fires an email notification if the average number of running pods drops below 8 over a 5-minute window - catching silent failures where pods crash without pipeline involvement.

<img width="1244" height="588" alt="alerts" src="https://github.com/user-attachments/assets/56175c7d-315d-4d89-9033-c0af790ef0c0" />

<p align="center"><strong>Azure Monitor alert configured to fire when pod count drops below 8.
</strong></p>


---

## What I Learned

The most time-consuming part wasn't writing the pipeline YAML - it was the ACR authentication issue. The AKS kubelet identity and the control plane identity are separate, and the `--attach-acr` flag assigns pull permissions to the wrong one. Debugging that forced me to understand how AKS managed identities actually work under the hood.

The canary pattern itself is deceptively simple at the pod level. Nine replicas plus one, behind a single service, and you have a real traffic split with zero additional infrastructure. What makes it meaningful is the pipeline logic around it: a deployment that automatically decides whether to promote or roll back based on observed health, not manual approval.

The cross-architecture build issue was also a good reminder that local and cloud environments aren't the same machine. Building for `linux/amd64` explicitly on Apple Silicon is the kind of thing that only surfaces when you're actually deploying to real infrastructure.

This project reflects how I approach infrastructure work: understand what's failing and why before reaching for a workaround, and build pipelines that handle failure as a first-class concern.
