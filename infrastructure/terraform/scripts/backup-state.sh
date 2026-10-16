#!/usr/bin/env bash
# Encrypted backup of the Terraform state + tfvars so the team is not tied to
# one laptop. Encrypted with age to every member's SSH PUBLIC key: any member
# can decrypt with their own SSH key, nobody else can. Never commit the output.
#
# usage: backup-state.sh <recipients-file> [remote-host]
#   recipients-file  one SSH public key per line (ssh-ed25519 / ssh-rsa), kept private
#   remote-host      optional SSH host; the file is stored root-only in /var/backups/scc26
# restore (any member):
#   age -d -i ~/.ssh/<your-key> scc26-tfstate-<stamp>.tar.age | tar x
set -euo pipefail

recipients=${1:?usage: backup-state.sh <recipients-file> [remote-host]}
remote=${2:-}
env_dir="$(cd "$(dirname "$0")/../environment" && pwd)"
out_dir="${SCC26_BACKUP_DIR:-$HOME/.config/scc26-secrets}"
stamp="$(date -u +%Y%m%dT%H%M%SZ)"
out="$out_dir/scc26-tfstate-$stamp.tar.age"

command -v age >/dev/null || { echo "age is required (https://github.com/FiloSottile/age)" >&2; exit 1; }
[ -s "$env_dir/terraform.tfstate" ] || { echo "no terraform.tfstate in $env_dir" >&2; exit 1; }
[ -s "$recipients" ] || { echo "recipients file is empty: $recipients" >&2; exit 1; }

umask 077
tar -C "$env_dir" -cf - terraform.tfstate terraform.tfvars \
  | age -R "$recipients" -o "$out"
echo "encrypted: $out ($(grep -c . "$recipients") recipients)"

if [ -n "$remote" ]; then
  base="$(basename "$out")"
  scp -q "$out" "$remote:/tmp/$base"
  # shellcheck disable=SC2029  # $base is expanded locally on purpose
  ssh "$remote" "sudo install -d -m 0700 -o root -g root /var/backups/scc26 \
    && sudo install -m 0600 -o root -g root /tmp/$base /var/backups/scc26/$base \
    && rm -f /tmp/$base && sudo ls -l /var/backups/scc26/$base"
fi
