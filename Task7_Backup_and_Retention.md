# Task 7: Monitoring & Observability — Backup & Retention Report

Student Management API platform — Kind Kubernetes cluster, namespace
`student-platform-tf`.

---

## 1. What Persists, and How

| Data | Storage mechanism | Backed up? | Retention |
|---|---|---|---|
| Application data (student records, SQLite) | `student-api` PVC (100Mi, RWO, StorageClass `standard`, `local-path` provisioner) | **No** | Indefinite (no automatic expiry — grows until manually managed) |
| Metrics (Prometheus) | Prometheus's own local storage (in-container/emptyDir-backed, not a dedicated PVC in this setup) | **No** | Prometheus default retention (not explicitly overridden — default is 15 days) |
| Logs (Loki) | `loki-pvc` (1Gi, RWO, filesystem chunks store) | **No** | 168h (7 days), explicitly configured in `loki-config.yaml` → `limits_config.retention_period` |
| Dashboards & alert rules (Grafana) | Grafana's internal SQLite database (in-container, not externalized to a PVC) | **No** | N/A — lost entirely if the Grafana pod/PVC is lost, since it isn't persisted at all |
| Kubernetes manifests / Infrastructure-as-Code | Git repository (`~/StudentAPI`, pushed to GitHub as of this session) | **Yes** | Indefinite (version-controlled) |

**Key finding: nothing in the live cluster is actually backed up.** Everything
marked "No" above exists only as long as its PVC (or, for Grafana, its pod)
survives. The *definitions* (YAML manifests, Terraform, Ansible playbooks) are
safely in Git, but the **runtime data and state are not** — this is the most
important gap this report surfaces.

---

## 2. Specific Risks

### 2.1 Grafana Configuration Is Not Persisted at All
The `grafana` Deployment in this setup does not mount a PVC for
`/var/lib/grafana`, meaning the SQLite database holding the "Student API -
Overview" dashboard, all 5 alert rules, the `student-api-alerts` folder, the
Prometheus and Loki datasource configurations, and the contact point are
**stored only inside the running pod's writable container layer**. If the
Grafana pod is deleted and recreated (e.g., during a node reboot, an
out-of-memory eviction, or a rollout), **all of this is lost** and would need
to be rebuilt from scratch.

**This is the single highest-priority gap identified in this report.**

### 2.2 Prometheus Metrics History Has No Long-Term Retention
Prometheus's default retention (15 days, not explicitly configured otherwise
in this setup) means historical trend data beyond that window is
automatically discarded. For a training project this is acceptable, but it
means any long-term capacity trend analysis (see `Task7_Capacity_Analysis.md`)
can only look back 15 days at most.

### 2.3 SQLite Database Has No Backup or Point-in-Time Recovery
The application's actual data (student records) lives only in the PVC-backed
SQLite file. There is no scheduled export, snapshot, or off-cluster copy. If
the PVC is deleted or corrupted, the data is unrecoverable. This mirrors the
already-documented finding (Task 4/5) that SQLite-on-PVC gives persistence
across pod restarts, but not durability against PVC loss.

### 2.4 Loki's 7-Day Log Retention Means Historical Incident Evidence Expires
Since Loki retains logs for only 168h (7 days), any log-based evidence for an
incident older than a week is gone. For the incidents documented in
`Task7_Troubleshooting_Report.md`, the actual log excerpts were captured
manually into markdown reports specifically because Loki itself would not
have retained them long-term — this was, in effect, a manual backup workaround
adopted during the project, not a deliberate policy.

---

## 3. Recommendations (Not Yet Implemented)

These are documented as findings/recommendations for a future iteration, not
changes made in this project:

1. **Persist Grafana's data directory.** Add a PVC for `/var/lib/grafana` (or
   externalize dashboards/alerts as code via Grafana provisioning files
   checked into Git, which is the more GitOps-appropriate fix and would also
   solve the "not version-controlled" problem for dashboards/alerts, not just
   the "not backed up" problem).

2. **Add a scheduled SQLite export.** A simple CronJob that copies or dumps
   the SQLite file to a location outside the cluster (or at minimum, to a
   second PVC) on a schedule (e.g., daily) would close the biggest data-loss
   risk for actual application data.

3. **Consider increasing Prometheus retention** if longer historical trend
   analysis becomes a project requirement — currently left at default (15
   days), which is likely sufficient for a training project's timeframe but
   worth revisiting if capacity planning needs a longer baseline.

4. **Document Loki's retention trade-off explicitly** (done here) so future
   incident investigations know not to rely on Loki alone for anything older
   than 7 days — capture important log evidence into markdown reports (as
   already practiced) or extend retention if the PVC size (see
   `Task7_Capacity_Analysis.md`) can accommodate it.

5. **All Infrastructure-as-Code (Kubernetes manifests, Terraform, Ansible
   playbooks) is already correctly treated as the source of truth and is
   version-controlled in Git** — this part of the backup story is solid and
   should be maintained as the standard for anything added going forward
   (i.e., avoid manual `kubectl apply`-only changes that never make it into a
   committed manifest).

---

## 4. Summary

Configuration-as-code is well covered (Git). Runtime data and state are not
backed up anywhere: Grafana's dashboards/alerts exist only inside a
non-persisted container layer (highest risk), the application's SQLite data
has no export/backup path, Prometheus keeps 15 days of metrics by default,
and Loki explicitly retains only 7 days of logs. None of these gaps have
caused an actual incident yet in this training project, but they represent
real risk in the current setup and are documented here as concrete
recommendations for a future hardening pass.

*Prepared as part of Task 7 (Monitoring, Observability & Logging) deliverables.*
