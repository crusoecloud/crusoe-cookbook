
## Slurm Cluster Setup with GPU Monitoring

This guide will walk you through setting up a Slurm cluster on Crusoe Cloud and integrating GPUd for monitoring and Lepton AI for dashboarding.

**GPUd:** GPUd is a lightweight, real-time monitor for your cluster's GPUs. It detects and reports hardware and system-level issues, enabling earlier signaling of downtime.

**Lepton AI:** Lepton AI integrates with GPUd to offer a centralized dashboard for monitoring GPU health and performance across your cluster.

## Foundations

### 1. Clone the Slurm Crusoe Template Project

```bash
git clone https://github.com/crusoecloud/slurm.git
cd slurm
```

### 2. Populate `~/.crusoe/config`

Create or modify your `~/.crusoe/config` file with your Crusoe Cloud credentials:

```properties
[default]
access_key_id = "your_access_key"
default_project = "default"
secret_key = "your_secret_key"
```

**Note:** Replace `"your_access_key"` and `"your_secret_key"` with your actual Crusoe Cloud access key and secret key.

### 3. Modify the Example `slurm/examples/example.tfvars`

Customize the `slurm/examples/example.tfvars` file with your specific cluster configuration:

```terraform
location = "your_cluster_location"
project_id = "your_project_id"
ssh_public_key_path = "~/.ssh/id_rsa.pub"
vpc_subnet_id = "your_vpn_subnet_id"

slurm_head_node_count = 1
slurm_head_node_type = "c1a.8x"
slurm_login_node_count = 1
slurm_login_node_type = "a40.1x"
slurm_nfs_node_type = "s1a.20x"
slurm_nfs_home_size = "128GiB"
slurm_compute_node_type = "a40.1x"
slurm_compute_node_count = 1

slurm_users = [{
  name = "your.name"
  uid = 1001
  ssh_pubkey = "ssh-rsa KEY00001 your.name@localhost"
}]
```

**Note:** Replace the placeholder values with your actual Crusoe Cloud location, project ID, SSH public key path, VPC subnet ID, and desired node configurations.

### 4. Install Ansible on the Controller Machine

Ansible is required to automate the installation of GPUd. Install it on your local machine or a designated controller machine.

**Debian/Ubuntu:**

```bash
sudo apt update
sudo apt install ansible
```

**Red Hat/CentOS:**

```bash
sudo yum install ansible
```

**macOS:**

```bash
brew install ansible
```

### 5. Initialize and Apply Terraform

Initialize and apply the Terraform configuration to create your Slurm cluster:

```bash
terraform init
terraform apply
```

## GPUd Installation and Configuration

### 1. Create an Ansible Playbook `./gpud_install.yml`

Create a new file named `gpud_install.yml` with the following content:

```yaml
---
- name: Install and Configure gpud
  hosts: all
  become: true
  user: ubuntu
  tasks:
    - name: Check if GPU is present
      shell: lspci | grep -i nvidia
      register: gpu_check
      ignore_errors: true
      changed_when: false

    - name: Skip if no GPU found
      when: gpu_check.rc != 0
      debug:
        msg: "No NVIDIA GPU detected. Skipping gpud installation on {{ inventory_hostname }}."

    - name: Install gpud
      when: gpu_check.rc == 0
      block:
        - name: Download and execute gpud install script
          shell: curl -fsSL https://pkg.gpud.dev/install.sh | sh
          register: gpud_install_output

        - name: Start gpud with optional Lepton AI token
          shell: "sudo gpud up {{ ' --token ' + lepton_ai_token if lepton_ai_token is defined else '' }}"
          register: gpud_up_output
          changed_when: "'successfully started gpud' not in gpud_up_output.stdout"

        - name: Display gpud start output
          debug:
            msg: "{{ gpud_up_output.stdout }}"
        - name: Display gpud install output
          debug:
            msg: "{{ gpud_install_output.stdout }}"
```

### 2. Configure Ansible Inventory

Generate an Ansible inventory file (`hosts.ini`) containing the public IP addresses of your Slurm nodes:

```bash
crusoe compute vms list -f json | jq -r '.[] | "\(.name) ansible_host=\(.network_interfaces[0].ips[0].public_ipv4.address)"' > ./hosts.ini
```

### 3. Run the Ansible Playbook

#### Local Dashboards Only

To install GPUd and access the local dashboards, run the following command:

```bash
ansible-playbook -i ./hosts.ini ./gpud_install.yml
```

#### Local Dashboard Access

After running the playbook, you can access the local GPUd dashboard by creating an SSH tunnel.

_Assuming `204.52.16.221` is the public IP address of a Slurm node_

```bash
ssh -f your.name@204.52.16.221 -L 15132:localhost:15132 -N
```

Then, open a web browser and navigate to `http://localhost:15132`.

#### Using Lepton.ai

To integrate with Lepton AI, you need to provide your Lepton AI token:

```bash
ansible-playbook -i ./hosts.ini ./gpud_install.yml -e "lepton_ai_token=<YOUR_LEPTON_AI_TOKEN>"
```

**Note:** Replace `<YOUR_LEPTON_AI_TOKEN>` with your actual Lepton AI token.

#### Connect to Lepton.ai Dashboard

If you provided a Lepton AI token, your nodes should now be connected to your Lepton AI dashboard. You can view the GPU metrics in the Lepton AI dashboard under **Utilities -> Machines**.

