# Argo CD child Applications

The root Application (`gitops/bootstrap/root-application.yaml`) watches this directory on `dev`. Each `*.yaml` here is one Argo CD `Application`, with its values under `gitops/resources/<name>/`.

Planned order (week2/README.md):

1. Cinder CSI and StorageClasses, with sealed OpenStack credentials (Part E)
2. Traefik, cert-manager and the DNS/TLS baseline (Part F)
3. Cilium: Argo adopts the Helm release from `gitops/resources/cilium/values.yaml` (its own reviewed PR; adopting a live CNI has to be done carefully)

Rules (gitops/README.md): no plaintext secrets, pinned versions/digests, no `kubectl edit` as a deployment method.
