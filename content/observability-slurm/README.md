# Installing observability stack on SLURM

## Automatic
The easiest way of creating SLURM cluster with observability stack enabled is to use our Terraform/Ansible script. Make sure to enable observability in your values:
```hcl
enable_observability = true
```

## Manual steps

### Prerequisites
- SLURM Cluster: A functioning SLURM cluster with head nodes and compute nodes.
- Administrative Access: Root or sudo privileges on all nodes.
- Internet Access: Nodes must be able to download packages from the internet.
- NVIDIA GPUs: Compute nodes with NVIDIA GPUs and drivers properly installed.
- Operating System: Ubuntu 20.04 or newer
- Firewall: Ability to configure firewall rules for required ports

### Security Considerations
Before proceeding with installation, please note:
- Configure firewall rules to restrict access to the following ports:
  - Prometheus (9090)
  - Node Exporter (9100)
  - DCGM Exporter (9400)
  - Grafana (3000 - only on the head node)
- Use SSL/TLS certificates for secure communication
- Use secrets management for sensitive credentials
- Implement authentication for all services
- Regular security updates and monitoring

### Installation steps

#### 1. *Update System and Install Dependencies*
   
_On all nodes_

Update package lists and install required packages:
```bash
$ sudo apt update
$ sudo apt install -y curl wget gnupg2 software-properties-common apt-transport-https ca-certificates
```

#### 2. *Create Users and Directories*

_On all nodes_

 Create users for Prometheus and Node Exporter:
 ```bash
$ sudo useradd --no-create-home --shell /usr/sbin/nologin prometheus
$ sudo useradd --no-create-home --shell /usr/sbin/nologin node_exporter
```
Create directories:
```bash
$ sudo mkdir /etc/prometheus
$ sudo mkdir /var/lib/prometheus
```

Set ownership:
```
sudo chown prometheus:prometheus /etc/prometheus
sudo chown prometheus:prometheus /var/lib/prometheus
```

#### 3. *Install and configure Prometheus*

_On head node_

Download Prometheus:
```bash
$ cd /tmp
$ wget https://github.com/prometheus/prometheus/releases/download/v2.48.1/prometheus-2.48.1.linux-amd64.tar.gz
```

Install Prometheus:
```bash
tar xvf prometheus-2.48.1.linux-amd64.tar.gz
sudo mv prometheus-2.48.1.linux-amd64 /opt/prometheus
```

Create symbolic links for binaries:
```bash
$ sudo ln -s /opt/prometheus/prometheus /usr/local/bin/prometheus
$ sudo ln -s /opt/prometheus/promtool /usr/local/bin/promtool
```

Set ownership:
```bash
$ sudo chown -R prometheus:prometheus /opt/prometheus
```

- Configure Prometheus

Create the configuratino file at `/etc/prometheus/prometheus.yaml`:
```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']

  - job_name: 'node_exporter'
    static_configs:
      - targets:
        - 'localhost:9100'

  - job_name: 'dcgm_exporter'
    static_configs:
      - targets:
        - 'localhost:9400'

  - job_name: 'slurm_nodes'
    static_configs:
      - targets:
        # Replace with the IP addresses or hostnames of compute nodes
        - 'compute-node-1:9100'
        - 'compute-node-2:9100'
        # Add more compute nodes as needed
```

Set ownership:
```bash
$ sudo chown prometheus:prometheus /etc/prometheus/prometheus.yml
```

- Create Systemd service for Prometheus

Create a file at `/etc/systemd/system/prometheus.service` with contents:
```
[Unit]
Description=Prometheus Monitoring
Wants=network-online.target
After=network-online.target

[Service]
User=prometheus
Group=prometheus
Type=simple
ExecStart=/usr/local/bin/prometheus \
  --config.file=/etc/prometheus/prometheus.yml \
  --storage.tsdb.path=/var/lib/prometheus/ \
  --web.console.templates=/opt/prometheus/consoles \
  --web.console.libraries=/opt/prometheus/console_libraries

[Install]
WantedBy=multi-user.target
```

Reload systemd and start Prometheus.

```bash
$ sudo systemctl daemon-reload
$ sudo systemctl enable prometheus
$ sudo systemctl start prometheus
```

#### 4. Install Node Exporter

_On all nodes_

Download Node exporter:
```bash
$ cd /tmp
$ wget https://github.com/prometheus/node_exporter/releases/download/v1.8.2/node_exporter-1.8.2.linux-amd64.tar.gz
```

Install Node Exporter:
```bash
$ tar xvf node_exporter-1.8.2.linux-amd64.tar.gz
$ sudo mv node_exporter-1.8.2.linux-amd64 /opt/node_exporter
```

Create a symbolic link:
```bash
$ sudo ln -s /opt/node_exporter/node_exporter /usr/local/bin/node_exporter
```

Set ownership:
```bash
$ sudo chown -R node_exporter:node_exporter /opt/node_exporter
```

Create Systemd service for Node Exporter at `/etc/systemd/system/node_exporter.service` with contents:
```
[Unit]
Description=Node Exporter
Wants=network-online.target
After=network-online.target

[Service]
User=node_exporter
Group=node_exporter
Type=simple
ExecStart=/usr/local/bin/node_exporter \
  --collector.systemd \
  --collector.processes

[Install]
WantedBy=multi-user.target
```

Reload systemd and start Node Exporter:
```bash
$ sudo systemctl daemon-reload
$ sudo systemctl enable node_exporter
$ sudo systemctl start node_exporter
```

#### 5. Install DCGM

_Compute nodes with NVidia GPUs_

Install Docker:
```bash
$ sudo apt update
$ sudo apt install -y docker.io
```

Start and enable Docker:
```bash
$ sudo systemctl start docker
$ sudo systemctl enable docker
```

Install NVidia Container Toolkit
```bash
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/libnvidia-container/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/libnvidia-container/$distribution/libnvidia-container.list | \
  sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list
```

Update apt repository and install container toolkit:
```bash
$ sudo apt update
$ sudo apt install -y nvidia-container-toolkit
$ sudo systemctl restart docker
```

Run DCGM Exporter container:
```bash
$ sudo docker run -d --restart always \
  --gpus all \
  -p 9400:9400 \
  --name dcgm-exporter \
  nvcr.io/nvidia/k8s/dcgm-exporter:3.3.9-3.6.1-ubuntu22.04
```

#### 6. Install Grafana

_Head node only_

Add Grafana repository:
```bash
$ sudo apt install -y gnupg2
$ curl https://packages.grafana.com/gpg.key | sudo apt-key add -

$ echo "deb https://packages.grafana.com/oss/deb stable main" | \
  sudo tee /etc/apt/sources.list.d/grafana.list
```

Install Grafana:

```bash
sudo apt update
sudo apt install -y grafana
```

Configure Grafana:

Edit the Grafana configuration file at `/etc/grafana/grafana.ini` and set following settings:

```ini
[server]
http_addr = 0.0.0.0
http_port = 3000

[security]
admin_user = admin
admin_password = ${GRAFANA_ADMIN_PASSWORD}

[auth.anonymous]
enabled = false

[users]
allow_sign_up = false

[analytics]
reporting_enabled = false
```

Finally, start Grafana service:
```bash
$ sudo systemctl daemon-reload
$ sudo systemctl enable grafana-server
$ sudo systemctl start grafana-server
```

Now you're ready to access Grafana dashboard. Open a web browser and navigate to http://<head-node-ip>:3000.
Login with:
- username: admin
- password: `your_secure_password` (set in the Grafana configuration)

Add Prometheus data source, for endpoint URL use `http://localhost:9090`.

#### 7. Import Dashboards

In Grafana, go to Dashboards -> New -> Import

*GPU Monitoring Dashboard*

Paste the following JSON in the import section:

```json
{
  "title": "GPU Monitoring",
  "uid": "gpu-monitoring",
  "panels": [
    {
      "title": "GPU Utilization",
      "type": "timeseries",
      "gridPos": { "x": 0, "y": 0, "w": 12, "h": 8 },
      "datasource": "Prometheus",
      "targets": [
        { "expr": "DCGM_FI_DEV_GPU_UTIL", "refId": "A" }
      ],
      "fieldConfig": { "defaults": { "unit": "percent" } }
    },
    {
      "title": "GPU Memory Usage",
      "type": "timeseries",
      "gridPos": { "x": 12, "y": 0, "w": 12, "h": 8 },
      "datasource": "Prometheus",
      "targets": [
        { "expr": "DCGM_FI_DEV_FB_USED", "refId": "A" }
      ],
      "fieldConfig": { "defaults": { "unit": "bytes" } }
    }
    // Add more panels as needed
  ],
  "time": { "from": "now-6h", "to": "now" },
  "refresh": "5s"
}
```

Similarily, add the Node Metrics dashboard with following example JSON:
```json
{
  "title": "Node Metrics",
  "uid": "node-metrics",
  "panels": [
    {
      "title": "CPU Usage",
      "type": "timeseries",
      "gridPos": { "x": 0, "y": 0, "w": 12, "h": 8 },
      "datasource": "Prometheus",
      "targets": [
        {
          "expr": "100 - (avg by (instance) (irate(node_cpu_seconds_total{mode='idle'}[5m])) * 100)",
          "refId": "A"
        }
      ],
      "fieldConfig": { "defaults": { "unit": "percent" } }
    },
    {
      "title": "Memory Usage",
      "type": "timeseries",
      "gridPos": { "x": 12, "y": 0, "w": 12, "h": 8 },
      "datasource": "Prometheus",
      "targets": [
        {
          "expr": "node_memory_MemTotal_bytes - node_memory_MemAvailable_bytes",
          "refId": "A"
        }
      ],
      "fieldConfig": { "defaults": { "unit": "bytes" } }
    }
    // Add more panels as needed
  ],
  "time": { "from": "now-6h", "to": "now" },
  "refresh": "5s"
}
```

#### 8. Verify the installation

- Open Prometheus web interface: http://(head-node-ip):9090/targets
- Ensure that all targets (Node Exporter, DCGM Exporter) are up.

*View Grafana Dashboards*:
- Open each dashboard in Grafana.
- Verify that metrics are being displayed correctly.

### Additional notes

#### Services management:

- To check the status of services:

```bash
$ sudo systemctl status prometheus
$ sudo systemctl status node_exporter
$ sudo systemctl status grafana-server
```

- To restart services if needed:

```bash
$ sudo systemctl restart prometheus
$ sudo systemctl restart node_exporter
$ sudo systemctl restart grafana-server
```

- Logs:
  - Prometheus logs can be found by executing `sudo journalctl -u prometheus`
  - Node Exporter logs can be found by executing `sudo journalctl -u node_exporter`
  - Grafana logs can be found at `/var/log/grafana/`

### Troubleshooting

#### Common Issues and Solutions

1. **Service Won't Start**
   ```bash
   # Check service status
   sudo systemctl status <service-name>
   # View logs
   sudo journalctl -u <service-name> -f
   ```

2. **Metrics Not Showing**
   - Verify target is up in Prometheus UI
   - Check network connectivity
   - Verify port accessibility: `netstat -tulpn | grep <port>`

3. **GPU Metrics Missing**
   - Verify NVIDIA drivers: `nvidia-smi`
   - Check DCGM container logs: `docker logs dcgm-exporter`
   - Verify DCGM endpoint: `curl localhost:9400/metrics`

### Backup Procedures

1. **Prometheus Data**
   ```bash
   sudo systemctl stop prometheus
   sudo tar -czf prometheus_data_backup.tar.gz /var/lib/prometheus
   sudo systemctl start prometheus
   ```

2. **Grafana**
   ```bash
   sudo cp /etc/grafana/grafana.ini /etc/grafana/grafana.ini.backup
   sudo tar -czf grafana_data_backup.tar.gz /var/lib/grafana
   ```

### Upgrade Procedures

Always backup data before upgrading:

1. **Prometheus Upgrade**
   ```bash
   sudo systemctl stop prometheus
   # Download new version
   # Replace binaries
   # Test configuration
   sudo -u prometheus /usr/local/bin/prometheus --config.file=/etc/prometheus/prometheus.yml --check
   sudo systemctl start prometheus
   ```

2. **Node Exporter Upgrade**
   ```bash
   sudo systemctl stop node_exporter
   # Download new version
   # Replace binary
   sudo systemctl start node_exporter
   ```

### Health Monitoring

Set up alerting rules in Prometheus for:
- Service availability
- High resource usage
- Error rates
- GPU-specific metrics

Example alert rules can be added to `/etc/prometheus/alerts.yml`:
```yaml
groups:
- name: example
  rules:
  - alert: HighCPUUsage
    expr: 100 - (avg by(instance) (rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100) > 90
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: High CPU usage on {{ $labels.instance }}
```

### Network Topology

For a typical SLURM cluster with observability stack, the network layout should look like this:

```
                                    ┌─────────────────┐
                                    │                 │
                                    │  Head Node      │
                                    │  - Prometheus   │
                                    │  - Grafana      │
                                    │                 │
                                    └────────┬────────┘
                                            │
                                            │
                     ┌──────────────────────┼──────────────────────┐
                     │                      │                      │
             ┌───────┴───────┐      ┌───────┴───────┐      ┌───────┴───────┐
             │ Compute Node 1 │      │ Compute Node 2 │      │ Compute Node n │
             │ - Node Exporter│      │ - Node Exporter│      │ - Node Exporter│
             │ - DCGM Exporter│      │ - DCGM Exporter│      │ - DCGM Exporter│
             └───────────────┘      └───────────────┘      └───────────────┘
```

### Data Retention and Storage

Configure data retention in Prometheus by adding to `/etc/prometheus/prometheus.yml`:
```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s
  # How long to retain data
  retention_time: 15d
  # Maximum size of storage blocks
  storage.tsdb.max_block_duration: 4h
```

Storage requirements estimation:
- Prometheus: ~1MB/day per time series
- Grafana: ~100MB for dashboard configurations
- Node Exporter: negligible local storage
- DCGM: negligible local storage

### High Availability Setup

For production environments, consider setting up Prometheus in HA mode:

1. **Multiple Prometheus Instances**
   ```yaml
   # prometheus1.yml
   global:
     external_labels:
       replica: prometheus1
   
   # prometheus2.yml
   global:
     external_labels:
       replica: prometheus2
   ```

2. **Load Balancer Configuration**
   ```nginx
   upstream prometheus {
       server prometheus1:9090;
       server prometheus2:9090 backup;
   }
   ```

3. **Grafana HA Setup**
   ```ini
   [database]
   type = postgres
   host = postgres-server:5432
   name = grafana
   user = grafana
   ```

### Advanced Configuration

#### Prometheus Recording Rules
Add to `/etc/prometheus/rules/recording_rules.yml`:
```yaml
groups:
  - name: cpu_rules
    rules:
      - record: job:node_cpu_usage:avg_rate5m
        expr: 100 - avg by (job, instance) (rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100

  - name: gpu_rules
    rules:
      - record: job:gpu_memory_usage:avg
        expr: avg by (gpu) (DCGM_FI_DEV_FB_USED / DCGM_FI_DEV_FB_TOTAL) * 100
```

#### Service Discovery
Replace static configs with service discovery in `/etc/prometheus/prometheus.yml`:
```yaml
scrape_configs:
  - job_name: 'node'
    file_sd_configs:
      - files:
        - '/etc/prometheus/targets/*.yml'
        refresh_interval: 5m
```

#### Security Hardening

1. **TLS Configuration for Prometheus**
   ```yaml
   tls_config:
     cert_file: /etc/prometheus/ssl/prometheus.crt
     key_file: /etc/prometheus/ssl/prometheus.key
     client_auth_type: RequireAndVerifyClientCert
     ca_file: /etc/prometheus/ssl/ca.crt
   ```

2. **Authentication for Node Exporter**
   ```yaml
   basic_auth_config:
     username: ${NODE_EXPORTER_USER}
     password: ${NODE_EXPORTER_PASSWORD}
   ```

### Performance Tuning

1. **Prometheus Memory Management**
   Add to systemd service file:
   ```ini
   [Service]
   Environment="GOGC=40"
   Environment="GOMAXPROCS=4"
   ```

2. **Query Optimization**
   - Use recording rules for frequently used queries
   - Limit the use of regex in queries
   - Use appropriate time ranges in dashboards

### Disaster Recovery

1. **Backup Strategy**
   ```bash
   #!/bin/bash
   # /usr/local/bin/backup-metrics.sh
   
   BACKUP_DIR="/backup/metrics"
   DATE=$(date +%Y%m%d)
   
   # Prometheus
   systemctl stop prometheus
   tar -czf $BACKUP_DIR/prometheus-$DATE.tar.gz /var/lib/prometheus
   systemctl start prometheus
   
   # Grafana
   systemctl stop grafana-server
   tar -czf $BACKUP_DIR/grafana-$DATE.tar.gz /var/lib/grafana
   systemctl start grafana-server
   
   # Configurations
   tar -czf $BACKUP_DIR/configs-$DATE.tar.gz /etc/prometheus /etc/grafana
   
   # Cleanup old backups
   find $BACKUP_DIR -type f -mtime +30 -delete
   ```

2. **Recovery Procedure**
   ```bash
   #!/bin/bash
   # /usr/local/bin/restore-metrics.sh
   
   BACKUP_DIR="/backup/metrics"
   DATE=$1
   
   systemctl stop prometheus grafana-server
   
   tar -xzf $BACKUP_DIR/prometheus-$DATE.tar.gz -C /
   tar -xzf $BACKUP_DIR/grafana-$DATE.tar.gz -C /
   tar -xzf $BACKUP_DIR/configs-$DATE.tar.gz -C /
   
   chown -R prometheus:prometheus /var/lib/prometheus /etc/prometheus
   chown -R grafana:grafana /var/lib/grafana /etc/grafana
   
   systemctl start prometheus grafana-server
   ```

### Maintenance Schedule

Recommended maintenance schedule:
- Daily: Check alerts and service status
- Weekly: Review storage usage and performance metrics
- Monthly: Backup data and configurations
- Quarterly: Review and update alert thresholds
- Bi-annually: Version upgrades and security audits