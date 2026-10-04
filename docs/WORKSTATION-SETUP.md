# Workstation setup (Week 1, Phase 1)

Every team member sets up the same toolset so anyone can run Terraform/Ansible. Everything here installs into your **home directory**: no `sudo`, nothing system-wide, and every binary download is checked against its published SHA-256.

## 0. Windows users: use WSL2 Ubuntu

Ansible's control node does not run on native Windows. Open PowerShell:

```powershell
# RUN ON: WORKSTATION (Windows PowerShell)
wsl --install -d Ubuntu
```

Do **all** project work inside the Ubuntu terminal. Ignore any `kubectl` that Docker Desktop put on your Windows PATH; we never use kubectl from workstations.

## 1. Private directories for credentials

```bash
# RUN ON: WORKSTATION
mkdir -p ~/.local/bin ~/.config/openstack ~/.config/scc26-secrets
chmod 700 ~/.config/openstack ~/.config/scc26-secrets
grep -q '.local/bin' ~/.bashrc || echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

## 2. uv (installs the Python tools in isolated environments)

```bash
# RUN ON: WORKSTATION
cd "$(mktemp -d)"
UV=$(curl -fsSL https://api.github.com/repos/astral-sh/uv/releases/latest | python3 -c 'import sys,json;print(json.load(sys.stdin)["tag_name"])')
curl -fsSLO https://github.com/astral-sh/uv/releases/download/$UV/uv-x86_64-unknown-linux-gnu.tar.gz
curl -fsSLO https://github.com/astral-sh/uv/releases/download/$UV/uv-x86_64-unknown-linux-gnu.tar.gz.sha256
sha256sum -c uv-x86_64-unknown-linux-gnu.tar.gz.sha256
tar xzf uv-x86_64-unknown-linux-gnu.tar.gz
cp uv-x86_64-unknown-linux-gnu/uv uv-x86_64-unknown-linux-gnu/uvx ~/.local/bin/
```

## 3. Terraform

```bash
# RUN ON: WORKSTATION
cd "$(mktemp -d)"
TF=1.16.5   # team baseline; instructor minimum is >= 1.9
curl -fsSLO https://releases.hashicorp.com/terraform/$TF/terraform_${TF}_linux_amd64.zip
curl -fsSLO https://releases.hashicorp.com/terraform/$TF/terraform_${TF}_SHA256SUMS
grep linux_amd64.zip terraform_${TF}_SHA256SUMS | sha256sum -c -
unzip -oq terraform_${TF}_linux_amd64.zip terraform -d ~/.local/bin/
```

## 4. kubeseal (needed from Week 2)

```bash
# RUN ON: WORKSTATION
cd "$(mktemp -d)"
KS=0.40.0   # team baseline
curl -fsSLO https://github.com/bitnami-labs/sealed-secrets/releases/download/v$KS/kubeseal-$KS-linux-amd64.tar.gz
curl -fsSLO https://github.com/bitnami-labs/sealed-secrets/releases/download/v$KS/sealed-secrets_${KS}_checksums.txt
grep kubeseal-$KS-linux-amd64.tar.gz sealed-secrets_${KS}_checksums.txt | sha256sum -c -
tar xzf kubeseal-$KS-linux-amd64.tar.gz kubeseal && install -m 755 kubeseal ~/.local/bin/
```

## 5. OpenStack CLI and Ansible

```bash
# RUN ON: WORKSTATION
uv tool install --python 3.12 python-openstackclient==10.3.0
uv tool install --python 3.12 --with ansible-core==2.21.4 --with-executables-from ansible-core ansible
```

## 6. Verify and report

```bash
# RUN ON: WORKSTATION
git --version; ssh -V; openstack --version; terraform version | head -1
ansible --version | head -1; kubeseal --version
command -v kubectl || echo "kubectl not installed (correct)"
```

Post the output in the Week-1 workstation issue. Do **not** paste anything from `~/.config/openstack`.

## Team baseline versions

| Tool | Version |
| --- | --- |
| Terraform | 1.16.5 |
| kubeseal | 0.40.0 |
| OpenStack CLI (python-openstackclient) | 10.3.0 |
| Ansible (ansible-core) | 2.21.4 |
