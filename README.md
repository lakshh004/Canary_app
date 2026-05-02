# 🚀 Canary Deployment Pipeline on Azure DevOps + AKS

[![Azure DevOps](https://img.shields.io/badge/Azure_DevOps-Pipeline-blue)](https://dev.azure.com)
[![AKS](https://img.shields.io/badge/AKS-Kubernetes-326CE5)](https://azure.microsoft.com/en-us/products/kubernetes-service)
[![ACR](https://img.shields.io/badge/ACR-Container_Registry-0078D4)](https://azure.microsoft.com/en-us/products/container-registry)
[![Docker](https://img.shields.io/badge/Docker-linux%2Famd64-blue)](https://docker.com)
[![Status](https://img.shields.io/badge/Pipeline-PASSING-brightgreen)]()

---

## Project Overview

This project implements a canary deployment pipeline on Azure DevOps that automatically routes 10% of live traffic to a new release while keeping 90% on the stable version. If the canary passes a health check after 2 minutes, the pipeline promotes it to stable. If it fails, it rolls back automatically — without any manual intervention.

The entire setup runs on a single-node AKS cluster using Azure Container Registry for image storage and Azure DevOps Pipelines for CI/CD automation. Every push to `main` triggers the full pipeline.

The pipeline handles:

- Automated Docker image build and push to ACR on every commit
- Canary deployment to AKS with 10% live traffic split
- 2-minute health stabilization window post-deploy
- Auto-promotion to stable if canary passes
- Auto-rollback if canary health check fails
- Azure Monitor alert if pod count drops below 8

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

## Architecture Breakdown

### Azure Region
`Central India`

### AKS Cluster (Standard_B2s_v2)

Single-node Kubernetes cluster running all workloads:

- **app-stable** — 9 replicas running the current stable image (`flask-app:stable`)
- **app-canary** — 1 replica running the new release (`flask-app:canary`)
- **flask-service** — LoadBalancer service selecting pods by `app: flask-app` label, routing to all 10 pods

The traffic split works at the pod level. With 9 stable and 1 canary pod behind a single service, roughly 10% of requests hit the canary — no Istio or ingress controller needed.

**ACR (lakshyaacr):**
- Stores `flask-app:stable` and `flask-app:canary` tags
- AKS pulls images using a Kubernetes `imagePullSecret` backed by ACR admin credentials

### Azure DevOps Pipeline

Pipeline defined in `azure-pipelines.yml` with four stages:

```yaml
stages:
  - Build
  - DeployCanary
  - HealthCheck
  - Promote
```

**Build** — builds Docker image for `linux/amd64` and pushes to ACR as `flask-app:canary`

**DeployCanary** — applies `canary-deployment.yaml` to AKS, bringing the new pod live alongside stable

**HealthCheck** — waits 2 minutes, then runs `kubectl rollout status` on the canary deployment. Passes or fails based on pod health.

**Promote** — only runs if HealthCheck passes. Rebuilds image as `flask-app:stable` and applies `stable-deployment.yaml`, completing the promotion.

### Azure Monitor

Pod count alert on `canary-aks`. Fires an email notification if the average number of running pods drops below 8 over a 5-minute window — catching silent failures where pods crash without pipeline involvement.

---

## Pipeline Stages

### Build

```bash
docker buildx build --platform linux/amd64 \
  -t lakshyaacr.azurecr.io/flask-app:canary \
  --push .
```

Built for `linux/amd64` explicitly — the AKS node runs AMD64 but the dev machine is ARM64 (Apple Silicon). Without the platform flag, the image would silently fail to run on the cluster.

### Deploy Canary (10% traffic)

```yaml
- task: KubernetesManifest@1
  inputs:
    action: deploy
    kubernetesServiceConnection: aks-connection
    manifests: k8s/canary-deployment.yaml
```

Deploys 1 canary pod alongside 9 stable pods. The shared LoadBalancer service routes ~10% of incoming requests to the canary automatically.

### Health Check + Auto-Promote or Rollback

```bash
sleep 120
kubectl rollout status deployment/app-canary --timeout=60s
```

If the canary deployment is healthy after 2 minutes, the Promote stage runs and the new image replaces stable. If not, the pipeline fails here and the canary is rolled back — stable pods continue serving 100% of traffic unaffected.

---

## Traffic Split

The 90/10 split is achieved without any service mesh. One Kubernetes Service selects all pods with label `app: flask-app`. With 9 stable replicas and 1 canary replica, the load balancer distributes traffic proportionally.

Verified by hitting the endpoint 20 times and observing the version distribution:

```bash
for i in {1..20}; do curl -s http://<EXTERNAL_IP>/ ; echo; done
```

<!-- SS 1: Replace with your curl loop screenshot showing v1/v2 mix -->

---

## Project Screenshots

<img width="1148" height="649" alt="all 4 stages green" src="https://github.com/user-attachments/assets/94a82023-3f42-48d0-8b10-20f54cd43042" />

<p align="center"><strong>Azure DevOps pipeline - all 4 stages passing: Build → DeployCanary → HealthCheck → Promote.</strong></p>

&nbsp;

<img width="508" height="173" alt="kubectl get pods" src="https://github.com/user-attachments/assets/5aaf93e3-c4a8-4a36-9821-85d2b9d83bed" />

<p align="center"><strong>AKS cluster - 9 stable pods and 1 canary pod all Running.</strong></p>

&nbsp;


<img width="786" height="513" alt="curl" src="https://github.com/user-attachments/assets/34ccffa5-f308-41cf-a668-18b286cfd104" />


<p align="center"><strong>curl command to check if 90:10 ratio is working.</strong></p>

&nbsp;

<img width="1458" height="924" alt="browser v1" src="https://github.com/user-attachments/assets/f7aa6d5a-ec3f-4aa8-8a63-698e0bca0f94" />

<p align="center"><strong>Live app responding from AKS LoadBalancer - canary deployment serving traffic.</strong></p>

&nbsp;

<img width="1244" height="588" alt="alerts" src="https://github.com/user-attachments/assets/56175c7d-315d-4d89-9033-c0af790ef0c0" />

<p align="center"><strong>Azure Monitor alert configured to fire when pod count drops below 8.</strong></p>

---

## What This Project Demonstrates

- Canary deployment strategy on Kubernetes without a service mesh
- Azure DevOps multi-stage pipeline with conditional promotion logic
- AKS cluster provisioning and management via Azure CLI
- ACR image storage with cross-architecture builds (ARM64 → AMD64)
- Kubernetes imagePullSecrets for private registry authentication
- Azure Monitor alerting on cluster health metrics
- End-to-end Azure DevOps toolchain: Repos, Pipelines, service connections

---

## Conclusion

This project taught me Azure's DevOps toolchain by building something that actually required understanding it, not just following steps. The most time-consuming part wasn't writing the pipeline YAML, it was the ACR authentication issue: the AKS kubelet identity and the control plane identity are separate, and the `--attach-acr` flag assigns pull permissions to the wrong one. Debugging that forced me to understand how AKS managed identities actually work under the hood.

The canary pattern itself is deceptively simple at the pod level. Nine replicas plus one, behind a single service — and you have a real traffic split with zero additional infrastructure. What makes it meaningful is the pipeline logic around it: a deployment that automatically decides whether to promote or roll back based on observed health, not manual approval.

The cross-architecture build issue was also a good reminder that local and cloud environments aren't the same machine. Building for `linux/amd64` explicitly on Apple Silicon is the kind of thing that only surfaces when you're actually deploying to real infrastructure.

This project reflects how I approach infrastructure work: understand what's failing and why before reaching for a workaround, and build pipelines that handle failure as a first-class concern.
