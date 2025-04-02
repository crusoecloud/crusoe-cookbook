# Integrating observability stack into your Kubernetes cluster

This cookbook outlines the process of setting up an observability stack in your Kubernetes cluster, including Prometheus, Grafana, and exporters for node and GPU metrics.

## Resource provisioning

The simplest way to provision a cluster on Crusoe is to use our [RKE2 Terraform](https://github.com/crusoecloud/crusoe-ml-rke2). Complete the steps described in that repository and make sure you have access to the cluster with `kubectl`.

## Installing Prometheus Operator
The prometheus Operator simplifies the deployment and management of Prometheus instances in Kubernetes.

### Steps
#### 1. Add Helm repository
```bash
$ helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
$ helm repo update
```
#### 2. Install Prometheus Operator

Create a file called `prometheus-values.yaml` with contents:
```yaml
prometheus:
  prometheusSpec:
    serviceMonitorSelectorNilUsesHelmValues: false
additionalScrapeConfigs:
- job_name: gpu-metrics
  scrape_interval: 1s
  metrics_path: /metrics
  scheme: http
  kubernetes_sd_configs:
  - role: endpoints
    namespaces:
    names:
    - gpu-operator
  relabel_configs:
  - source_labels: [__meta_kubernetes_endpoints_name]
    action: drop
    regex: .*-node-feature-discovery-master
  - source_labels: [__meta_kubernetes_pod_node_name]
    action: replace
    target_label: kubernetes_node
```

```bash
$ helm install prometheus-operator prometheus-community/kube-prometheus-stack \
    --namespace monitoring -f prometheus-values.yaml --create-namespace
```
#### 3. Verify the installation
```bash
$ kubectl --namespace monitoring get pods \
    -l "release=prometheus-operator"
```
Ensure all pods are working and in healthy state.

## Installing and configuring the NVidia GPU Operator with DCGM exporter
### Steps
#### 1. Install the GPU Operator using Helm:
```bash
$ helm repo add nvidia https://nvidia.github.io/gpu-operator
$ helm repo update
$ helm install --wait --generate-name \
    nvidia/gpu-operator \
    --set dcgmExporter.enabled=true \
    --set dcgmExporter.serviceMonitor.enabled=true \
    --set serviceMonitor.enabled=true \
    --namespace gpu-operator \
    --create-namespace
```
This command adds the NVIDIA Helm repository, updates the repositories, and installs the GPU Operator in the `gpu-operator` namespace. The `--wait` flag ensures that Helm waits for the operator's deployment to be completed and the `--create-namespace` flag creates the namespace if it doesn't exist.
#### 2. Verify the GPU Operator and driver Installation:
```bash
$ kubectl get pods -n gpu-operator
```
Make sure all pods are either in healthy state or have completed running.

## Installing and configuring Grafana
Grafana is a visualization tool that can be used to create dashboards for monitoring your Kubernetes cluster and applications, including GPU metrics collected by dcgm-exporter. If you installed Prometheus using the kube-prometheus-stack Helm chart, Grafana is already installed as part of that package. We'll now cover accessing Grafana and configuring data sources.

## Steps:
#### 1. Access Grafana:

If you used the `kube-prometheus-stack` Helm chart, you can access Grafana using port-forwarding:

```bash
$ kubectl -n monitoring port-forward svc/prometheus-operator-grafana 3000:80
```

Now, open your web browser and navigate to `http://localhost:3000`.

Alternatively, if you have an ingress controller setup, you can create an Ingress rule to expose Grafana. Here's an example Ingress configuration:

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
    name: grafana-ingress
    namespace: monitoring
    annotations:
    # Add any necessary annotations for your ingress controller
    kubernetes.io/ingress.class: nginx
    nginx.ingress.kubernetes.io/rewrite-target: /
spec:
    rules:
    - host: grafana.your-domain.com
    http:
        paths:
        - path: /
        pathType: Prefix
        backend:
            service:
            name: prometheus-operator-grafana
            port:
                number: 80
```

#### 2. Login to Grafana
The default credentials for Grafana when installed with the kube-prometheus-stack Helm chart are:
- Username: admin
- Password: You can get the password by running the following command:
```bash
$ kubectl -n monitoring get secret prometheus-operator-grafana -o jsonpath="{.data.admin-password}" | base64 --decode ; echo
```
You will be prompted to change the password after the first login.

#### 3. Configure Prometheus as a data source
If you installed Grafana using the `kube-prometheus-stack` Helm chart, the Prometheus data source should already be configured automatically. However, you can verify or manually add it if needed.

*   Go to *Connections* > *Data Sources*.
*   You should see a data source named `Prometheus` already configured.
*   If not, click *Add data source*, select *Prometheus*.
*   Enter the following details:
    *   **URL:**  `http://<service-name>.monitoring.svc.cluster.local:9090`
        *   Check the service name by running the following command:
        ```bash
        $ kubectl -n monitoring get svc
        ```
    *   **Name:** `Prometheus` (or any other name you prefer)
*   Click *Save & Test*. You should see a success message if the data source is configured correctly.

## Grafana dashboards
Grafana dashboards provide a visual representation of your cluster and application metrics. You can create custom dashboards or import pre-built ones. Here are some recommended dashboards for GPU observability:
- *Node Exporter Dashboard*: For general node metrics, including CPU, memory, and disk utilization, you can use the Node Exporter dashboard.
- *NVIDIA DCGM Exporter Dashboard*: The dcgm-exporter project provides a recommended Grafana dashboard that you can import. You can find the JSON definition in the dcgm-exporter GitHub repository under grafana-dashboards/dcgm-exporter-dashboard.json or download it directly from a running dcgm-exporter instance at [/dashboards/dcgm-exporter-dashboard.json](https://github.com/NVIDIA/dcgm-exporter/blob/main/grafana/dcgm-exporter-dashboard.json).

To import this dashboard:
- download the JSON file
- in Grafana, go to Dashboard (+) > New > Import
- upload the JSON file or paste the JSON content
- select the Prometheus data source you configured earlier
- click Import
- this dashboard provides comprehensive metrics about your GPUs, including utilization, temperature, power usage, memory usage, and more

## Running a distributed ML workflow

To demonstrate the observability stack in action, we'll deploy a multi-replica (distributed) machine learning job using PyTorch's Distributed Data Parallel (DDP). This example can span multiple nodes and GPUs, allowing you to observe distributed training in Grafana.

### Steps

1. **Deploy the GPU example**
   
   Save this as gpu-example.yaml:

   ```yaml
    apiVersion: v1
    kind: Pod
    metadata:
      name: gpu-operator-test
    spec:
      restartPolicy: OnFailure
      containers:
        - name: cuda-vector-add
          image: "nvcr.io/nvidia/k8s/cuda-sample:vectoradd-cuda11.7.1-ubuntu20.04"
          resources:
            limits:
              nvidia.com/gpu: 1
   ```

   Apply this resource to your cluster:
   ```bash
   kubectl apply -f gpu-example.yaml
   ```

2. **Observe GPU metrics in Grafana**

   - Open your Grafana dashboard (e.g., http://localhost:3000 if using port-forwarding).
   - Navigate to the NVIDIA DCGM Exporter dashboard (or a relevant GPU dashboard) you imported earlier.
   - You should see GPU metrics from each worker in the distributed job, including utilization, memory usage, temperature, etc.

3. **Clean up**

   When finished, delete the distributed PyTorch job to free your resources:
   ```bash
   kubectl delete -f distributed-pytorch-mnist.yaml
   ```

This example demonstrates how to deploy a distributed ML workload with PyTorch and monitor its GPU usage in Grafana. You can adapt this approach to suit your own ML pipelines and continuously gain insights into their resource consumption and performance.

## Security Considerations

Here are some high-level security considerations when running and monitoring a Kubernetes cluster:

- Role-Based Access Control (RBAC)  
  Ensure RBAC is properly configured so that users and service accounts only have the permissions they need. Limit cluster administrator privileges to only trusted users.
  
- Network Policies  
  Leverage Kubernetes Network Policies to control inbound and outbound traffic for both application pods and monitoring components. This helps limit the blast radius if a component is compromised.

- Secure Storage and Transmission  
  • Encrypt sensitive data at rest (etcd data, persistent volumes).  
  • Use TLS/SSL to secure in-flight communication between components (e.g., ingress traffic, Grafana, Prometheus, and other external connections).

- Least Privilege for Observability Tools  
  Ensure that observability tools (Prometheus, Grafana, exporters) only have the required permissions and do not expose credentials or other sensitive data unnecessarily.

- Regular Updates and Patching  
  Keep your Kubernetes cluster, observability components (Helm charts, container images), and underlying OS patched and up-to-date to mitigate known vulnerabilities.

- Secrets Management  
  Use Kubernetes secrets for storing sensitive information. Restrict access via RBAC to these secrets and ensure your CI/CD pipelines do not inadvertently expose credentials.

- Validate Third-Party Integrations  
  Monitor and review any third-party software, including Helm charts and container images, for potential security risks. Pin versions and maintain updated images from trusted sources.

Adopting these measures helps ensure that your observability stack and Kubernetes environment remain resilient against common security threats.

## Scalability and Redundancy

When designing your observability stack for Kubernetes, consider setting up highly-available replicas for critical components (such as Prometheus clusters, Grafana instances, and exporters) to avoid single points of failure. Use Kubernetes deployments or stateful sets with proper anti-affinity rules to ensure workloads are distributed across multiple nodes. Leverage efficient storage backends or object storage for large-scale metric retention. You can also employ horizontal pod autoscaling for your monitoring components based on resource utilization or incoming workload, ensuring that additional pods are provisioned during peak times automatically. This approach provides a resilient and scalable observability setup that can cope with growing workloads or unexpected spikes while maintaining reliable data collection and alerting.

As an example, you can configure a Horizontal Pod Autoscaler (HPA) for Prometheus to automatically adjust the number of replicas based on CPU usage:

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: prometheus-hpa
  namespace: monitoring
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: prometheus-operator-kube-prometheus-prometheus
  minReplicas: 1
  maxReplicas: 3
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
```