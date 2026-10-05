# CI checks on pull requests

`.github/workflows/ci.yml` runs on every pull request into `dev` or `main` (and manually via *Run workflow*). It uses **no credentials**: nothing touches Sebowa, OpenStack or the cluster.

| Job | What it checks | Runs when |
| --- | --- | --- |
| secret scan (gitleaks 8.30.1) | the full git history for keys, tokens and passwords | always |
| yamllint 1.38.0 | YAML syntax/style (config in `.yamllint`; long lines only warn) | always |
| terraform fmt + validate (1.16.5) | `fmt -check -recursive`; `init -backend=false` + `validate` for every root module outside `modules/` | once `infrastructure/terraform/**/*.tf` exists |
| ansible-lint + syntax-check (core 2.21.4, lint 26.9.0) | `--syntax-check` of `playbooks/*.yml` against `inventories/example/hosts.yml`, then `ansible-lint` | once `infrastructure/ansible/` has YAML |

## Running the same checks locally (WSL)

```bash
# RUN ON: WORKSTATION, from the repo root
terraform fmt -check -recursive infrastructure/terraform
terraform -chdir=infrastructure/terraform/environment init -backend=false && \
  terraform -chdir=infrastructure/terraform/environment validate
uvx yamllint==1.38.0 .
cd infrastructure/ansible && ansible-playbook -i inventories/example/hosts.yml playbooks/bootstrap.yml --syntax-check
```

## If the secret scan fails

Do **not** just delete the line and push again; the secret stays in Git history. Stop, tell the captain, and rotate the credential. Then decide together how to clean the history.

Action versions are pinned to commit SHAs; tool versions are pinned in the workflow `env:` block. Change them in a reviewed PR.
