I prepared a data-flow diagram to make the scope of this PR easier to review:

![Karmada Certificate Rotation - Data Flow Change](https://github.com/user-attachments/assets/2b9c0efb-2fad-4f93-b05e-df9e4cdfeba1)

This PR adds a new certificate rotation path to `karmadactl init` through `--cert-mode=rotate`.

High-level behavior:

- The existing install/generate flow remains the default behavior.
- The new rotate flow reuses existing CA material from current init-managed Secrets.
- It renews component identity certificates, also known as leaf certificates.
- It updates init-managed certificate Secrets and kubeconfig Secrets.
- It preserves existing Secret metadata during updates.
- It prints restart guidance; components are not restarted automatically.

Intentional non-goals in this PR:

- No root CA / Front-Proxy CA / Etcd CA rotation.
- No caBundle updates in kubeconfigs, WebhookConfiguration, APIService, or CRD conversion configs.
- No workload recreation.
- No automatic rollout restart.
- No Helm or Karmada Operator flow changes.
- No cert-manager integration.
- No new certificate watcher/controller, audit log, or monitoring metric.

The main reason for this scope is to keep the first version focused on leaf certificate renewal. CA rotation is a trust-root migration problem and should be handled separately, because it would require updating all trust consumers consistently.

Suggested follow-up split after this PR:

1. Documentation PR: add a user-facing certificate rotation guide, including the required command, original install flags, backup recommendation, and manual restart steps. This can align with `karmada-io/website#1014`.
2. Restart UX follow-up: discuss whether Karmada should add an optional restart helper later. The current PR only prints restart guidance.
3. CA rotation design: if the community wants root CA rotation, handle it as a separate design/PR for trust-root migration, including caBundle and kubeconfig updates.
4. Helm/operator parity: if maintainers want rotation support outside `karmadactl init`, split Helm and operator support into separate PRs.
5. Observability follow-up: if needed, discuss audit logs or metrics separately from the core rotation flow.

For review, I think the most important parts are:

- Whether `--cert-mode=rotate` is an acceptable UX.
- Whether reading existing CA material from init-managed Secrets is acceptable for this first version.
- Whether the update-only Secret behavior is safe enough.
- Whether the current non-goals are aligned with maintainers' expectations.
