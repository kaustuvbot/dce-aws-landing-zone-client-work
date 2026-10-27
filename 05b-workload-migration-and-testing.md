# 05b — Workload Migration and Testing Lab (Console-First)

Companion to [05-lza-pipeline-implementation-runbook.md](05-lza-pipeline-implementation-runbook.md)
and [05a-poc-configuration-and-network-demo.md](05a-poc-configuration-and-network-demo.md).
This lab migrates a small application and its data from the **Network** account source VPC to the
**NonProduction** account destination VPC across a Transit Gateway, then tests controls and
logging. It is a rehost of **application + data only** — no server or on-premises rehosting is
claimed.

**Lab topology assumed from 05a** (verify, do not assume):

| Item | Source (Network account) | Destination (NonProduction account) |
|---|---|---|
| VPC name | `DCE-POC-SOURCE-VPC` | `DCE-POC-VPC` |
| VPC CIDR | `10.10.0.0/16` | `10.20.0.0/16` |
| App subnets | 2 AZs, private, `APP-A` / `APP-B` | 2 AZs, private, `APP-A` / `APP-B` |
| TGW subnets | Present, attached to `DCE-POC-TGW` | Present, attached to `DCE-POC-TGW` |
| Routing | `10.20.0.0/16` via TGW | `10.10.0.0/16` via TGW |

Region is **eu-west-2 (London)** throughout. Costs are in scope: two EC2 instances, two TGW
attachments, and four interface endpoints charged per AZ.

---

## Phase 0 — Preconditions

1. **05a Stage 4 (tags) has passed** and the last pipeline run is green. Record the current
   Configuration source commit ID; you will need it for the negative test in Phase 9.
2. **Identity Center baseline done** (05 Phase G): the operator has access to Management,
   Network and NonProduction accounts. Record both workload account IDs.
3. **Control Tower enrollment healthy**, no pending enrollments.
4. **No concurrent pipeline runs.** One change, one review, one approval — throughout.

---

## Phase 1 — Identity and session baseline

- Identity Center → **AWS accounts** → confirm Network and NonProduction are both assigned to
  `Lab-Administrators` with `AdministratorAccess`. Re-test both from the access portal.
- Confirm the CloudShell / console session in each account. Work console-first: every step
  below is done in the AWS console unless it is explicitly an in-instance shell command.
- **Out of scope for this lab:** Entra ID federation, domain join, on-premises trust.

---

## Phase 2 — Preflight the SSM agent and required tooling

Select the latest AWS-owned Amazon Linux 2023 x86_64 AMI in London. Its bundled SSM
Agent must support `ssmmessages` (version 3.3.40.0 or newer). Do not assume an older
cached AMI is suitable. Verify the actual version after the instance registers.

In each account, **Systems Manager → Session Manager → Preferences**: inspect existing
logging/KMS requirements. This minimal endpoint set does not support enforced CloudWatch,
S3 or KMS session features without their additional private endpoints and permissions.
If required by your baseline, stop and resolve those dependencies; do not weaken the policy.

After opening each instance session in Phase 5, run:

```bash
set -e
test "$(whoami)" = ssm-user || { echo "Use the configured non-root lab user"; exit 1; }
for c in python3 curl tar sha256sum; do
  command -v "$c" >/dev/null 2>&1 || { echo "MISSING: $c"; exit 1; }
done
python3 -c 'import sqlite3; print("Python and SQLite ready")'
amazon-ssm-agent -version
```

**STOP if tooling is missing or registration fails.** No package downloads or internet
egress are provided. Inspect IAM profile, agent, endpoint private DNS and security groups.

---

## Phase 3 — Interface endpoints (before any EC2)

Create these **in each VPC** (Network `10.10.0.0/16` and NonProduction `10.20.0.0/16`), in
**eu-west-2**:

| Endpoint | Service | Subnet | Private DNS |
|---|---|---|---|
| 1 | `com.amazonaws.eu-west-2.ssm` | `APP-A` (private) | Enabled |
| 2 | `com.amazonaws.eu-west-2.ssmmessages` | `APP-A` (private) | Enabled |

In **each account / London**, create the security groups first:
1. **VPC → Security groups → Create security group**, name `dce-demo-app-sg`, select
   that account's demo VPC. Keep inbound empty; remove default outbound.
2. Create `dce-demo-endpoint-sg` in the same VPC. Inbound **HTTPS / TCP 443**, source
   **the app SG ID**. Remove default outbound; stateful response traffic is allowed.
3. Edit the app SG outbound: **HTTPS / TCP 443**, destination **the endpoint SG ID**.
   No public access, self-referencing rules or cross-account SG references are needed.
4. **VPC → Endpoints → Create endpoint → AWS services**. Search each exact service above,
   choose its **Interface** entry, select the correct VPC and **APP-A** subnet, enable
   private DNS, select `dce-demo-endpoint-sg`. Keep the default endpoint policy for this
   disposable lab; IAM still authorizes SSM actions. Create and wait for **Available**.
5. Repeat for the second service and for the other VPC. Record **four endpoint IDs**.

Single-AZ endpoints reduce demo cost; this is not a production high-availability design.
VPC DNS support/hostnames must be enabled. No NAT, internet gateway or S3 staging is needed.

---

## Phase 4 — Security groups and instance launch

### 4.1 Instance security group design

Reuse the **two app SGs created in Phase 3**. Initially they have no inbound rules and
only outbound TCP 443 to their local endpoint SG. Add cross-VPC /32 rules in 4.5 only.

### 4.2 Launch EC2 (one per account)

First create the role in **4.3**, then launch in **Network** and **NonProduction**:
**EC2 → Instances → Launch instances**, enter the name below and select these settings.

- **AMI**: Amazon Linux 2023, x86_64. Confirm the architecture on the AMI detail page.
- **Instance type**: `t3.micro`.
- **Subnet**: `APP-A` (private) in the account's own VPC.
- **Auto-assign public IP**: **off**.
- **Security group**: the SG from 4.1.
- **Storage**: EBS **gp3, 8 GiB**, **encrypted** (the AWS-managed `aws/ebs`
  key is sufficient unless your baseline requires another key).
- **Advanced / Instance metadata options**: **IMDSv2 required** (`HttpTokens = required`),
  `HttpPutResponseHopLimit = 1`, instance metadata endpoint **enabled** so SSM can obtain instance-role credentials.
- **IAM instance profile**: select `dce-demo-ssm-role` (created in Phase 4.3); the policy name is not the profile name.
- **Tags**: `Name = dce-demo-app-<source|dest>`, plus the baseline's mandatory tags
  (`Project=DCE-POC`). Do not invent additional required tags. Choose **Proceed without
  a key pair**: this lab uses Session Manager, not SSH. Launch and wait for both status checks.

### 4.3 IAM instance profile (create separately in EACH account)

In each account: **IAM → Roles → Create role → AWS service → EC2 → Next →**
policy `AmazonSSMManagedInstanceCore` → name `dce-demo-ssm-role` → Create role.

Do **not** create the role in one account and share it — roles are account-scoped and
cross-account use of an instance profile is not supported.

### 4.4 Record the private IPs

Write down, per instance:

- Source instance ID and **private IPv4** (in `10.10.0.0/16`)
- Destination instance ID and **private IPv4** (in `10.20.0.0/16`)

Call them `<SOURCE_IP>` and `<DEST_IP>`. You will use them as `/32` sources and destinations.

### 4.5 Narrow the cross-VPC rules (only after 4.4)

On the **source** instance SG, add:

- Inbound TCP **8001** from `<DEST_IP>/32` (transfer service)

On the **destination** instance SG, add:

- Inbound TCP **8000** from `<SOURCE_IP>/32` (application API)

And correspondingly, on the **source** instance SG add outbound TCP **8000** to `<DEST_IP>/32`,
and on the **destination** instance SG add outbound TCP **8001** to `<SOURCE_IP>/32`.

Keep every rule `/32` to the single recorded peer IP. No CIDR-wide rules, no SSH.

---

## Phase 5 — Open Session Manager sessions

1. **SSM → Session Manager → Start session** on the source instance, then on the destination
   instance. Use **two separate sessions**.
2. Confirm the agent registered: the instance appears in **Managed instances** with
   `PingStatus = Online` and a recent `AgentVersion`.
3. Confirm no session relies on public IP: the instance has no public IP and the SSM session
   succeeds — that is the evidence that the interface endpoints and IMDSv2 path work.
4. Leave both sessions open; you will need the source session throughout.

---

## Phase 6 — Deploy the demo application (idempotent, non-root)

Run the directory-creation block in **each** instance session. Create `app.py` on the **source only**; the destination receives it through the migration. The commands create `~/dce-demo` (i.e.
`/home/ssm-user/dce-demo`), owned by `ssm-user`, mode `0750`, and never `chmod 777` or run
as root.

```bash
set -e
BASE=/home/ssm-user/dce-demo
mkdir -p "$BASE" "$BASE/transfer"
chmod 750 "$BASE" "$BASE/transfer"
```

Create `$BASE/app.py` with the following content (paste into the session; it is a small,
self-contained Python **standard-library** application — `http.server` + `sqlite3`, no
third-party packages, no network calls):

```bash
cat > /home/ssm-user/dce-demo/app.py <<'PY'
#!/usr/bin/env python3
"""Demo API: synthetic records in SQLite. Stdlib only. No real data."""
import json
import os
import sqlite3
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "records.db")
PORT = int(os.environ.get("DEMO_PORT", "8000"))
MAX_BODY = 64 * 1024

SCHEMA = """
CREATE TABLE IF NOT EXISTS records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
"""

SEED = [
    ("alpha-widget", "synthetic"),
    ("beta-widget", "synthetic"),
    ("gamma-widget", "synthetic"),
]


def connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    if os.path.exists(DB_PATH):
        return  # never re-seed an existing database
    conn = connect()
    try:
        conn.executescript(SCHEMA)
        conn.executemany(
            "INSERT INTO records (name, category) VALUES (?, ?)", SEED
        )
        conn.commit()
    finally:
        conn.close()


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def _send(self, code, payload):
        body = json.dumps(payload).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/health":
            self._send(200, {"status": "ok", "port": PORT})
            return
        if self.path == "/records":
            conn = connect()
            try:
                rows = conn.execute(
                    "SELECT id, name, category, created_at FROM records ORDER BY id"
                ).fetchall()
                self._send(200, {"count": len(rows), "records": [dict(r) for r in rows]})
            finally:
                conn.close()
            return
        self._send(404, {"error": "not found"})

    def do_POST(self):
        if self.path != "/records":
            self._send(404, {"error": "not found"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            length = 0
        if length <= 0 or length > MAX_BODY:
            self._send(400, {"error": "invalid body length"})
            return
        raw = self.rfile.read(length)
        try:
            payload = json.loads(raw.decode())
            if not isinstance(payload, dict):
                raise ValueError("JSON object required")
            name = payload["name"]
            category = payload.get("category", "synthetic")
            if (not isinstance(name, str) or not 1 <= len(name) <= 200
                    or not isinstance(category, str) or not 1 <= len(category) <= 100):
                raise ValueError("name required")
        except (ValueError, KeyError, json.JSONDecodeError):
            self._send(400, {"error": "invalid json"})
            return
        conn = connect()
        try:
            cur = conn.execute(
                "INSERT INTO records (name, category) VALUES (?, ?)", (name, category)
            )
            conn.commit()
            row = conn.execute(
                "SELECT id, name, category, created_at FROM records WHERE id = ?",
                (cur.lastrowid,),
            ).fetchone()
            self._send(201, {"record": dict(row)})
        finally:
            conn.close()

    def log_message(self, fmt, *args):
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))


if __name__ == "__main__":
    init_db()
    server = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    sys.stderr.write("dce-demo listening on 0.0.0.0:%d\n" % PORT)
    server.serve_forever()
PY
```

Notes on the code: parameterized SQL only (no string-built queries), a hard 64 KiB body cap,
`GET` does not mutate, and the three seeded rows are synthetic. The database is created **only
if absent**, so re-running never duplicates the seed.

Start the app on the source instance:

```bash
cd /home/ssm-user/dce-demo
nohup python3 app.py > app.log 2>&1 &
echo $! > app.pid
sleep 2
cat app.pid
```

Record the **exact PID** from `app.pid`; you will use it to stop the app.

---

## Phase 7 — Source-side application demo

In the **source** session:

```bash
curl -s http://127.0.0.1:8000/health
curl -s http://127.0.0.1:8000/records
```

Expect `{"status": "ok", ...}` and a count of **3** synthetic records.

---

## Phase 8 — Transfer the application and data over the TGW

### 8.1 Stop the source app gracefully

In the source session:

```bash
PID=$(cat /home/ssm-user/dce-demo/app.pid)
kill "$PID"
sleep 2
ps -p "$PID" >/dev/null 2>&1 && echo "STILL RUNNING" || echo "STOPPED"
```

Stop source writes before the copy. Verify the PID belongs to this demo app before signalling
it; if it remains running, stop and investigate rather than copying a live database. This
app uses SQLite's default rollback journal and closes each connection after its request.
Check consistency after stopping:

```bash
python3 - <<'PY'
import sqlite3
c = sqlite3.connect("/home/ssm-user/dce-demo/records.db")
assert c.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
c.close()
print("Database integrity OK")
PY
```

### 8.2 Build the archive and its checksum

```bash
cd /home/ssm-user/dce-demo
sha256sum app.py records.db > SHA256SUMS
tar -czf transfer/dce-demo-bundle.tar.gz app.py records.db SHA256SUMS
sha256sum transfer/dce-demo-bundle.tar.gz | tee transfer/bundle.sha256
```

`SHA256SUMS` is **manifest only** — it records the expected digests of the extracted files. The
bundle's own digest is `bundle.sha256`; that is the value you compare **by eye** on the
destination.

### 8.3 Serve the archive over a dedicated transfer directory

Serve **only** `~/dce-demo/transfer` — never the home directory or the whole app directory.

```bash
cd /home/ssm-user/dce-demo/transfer
nohup python3 -m http.server 8001 --bind 0.0.0.0 > transfer-server.log 2>&1 &
echo $! > transfer.pid
```

Note the transfer PID separately from the app PID.

### 8.4 Destination pulls the archive through the TGW

In the **destination** session:

```bash
cd /home/ssm-user/dce-demo
mkdir -p transfer
curl --fail --max-time 30 -sS -o transfer/dce-demo-bundle.tar.gz http://<SOURCE_IP>:8001/dce-demo-bundle.tar.gz
ls -l transfer/
```

A successful download over the TGW is itself the TGW data-path evidence.

### 8.5 Verify integrity manually

```bash
cd /home/ssm-user/dce-demo
sha256sum transfer/dce-demo-bundle.tar.gz
# Compare with the bundle SHA-256 recorded from the SOURCE session in 8.2.
```

**Compare the two values by eye.** They must match character for character. Do not proceed on
a mismatch — re-transfer and re-check.

### 8.6 Extract only the known bundle

```bash
cd /home/ssm-user/dce-demo
tar -tzf transfer/dce-demo-bundle.tar.gz   # inspect the listing FIRST
tar -xzf transfer/dce-demo-bundle.tar.gz   # then extract
ls -la
```

The listing must contain only `app.py`, `records.db`, `SHA256SUMS`. Extract nothing else.

### 8.7 Verify the data arrived

```bash
cd /home/ssm-user/dce-demo
sha256sum -c SHA256SUMS
python3 - <<'PY'
import sqlite3
c = sqlite3.connect("/home/ssm-user/dce-demo/records.db")
print("record count:", c.execute("SELECT COUNT(*) FROM records").fetchone()[0])
for r in c.execute("SELECT id, name, category FROM records ORDER BY id"):
    print(r)
c.close()
PY
```

Expect a count of **3** (the synthetic seed).

### 8.8 Start the app on the destination and test through the TGW

```bash
cd /home/ssm-user/dce-demo
nohup python3 app.py > app.log 2>&1 &
echo $! > app.pid
```

In the **source** session (so traffic traverses the TGW, not localhost):

```bash
curl -s --max-time 10 http://<DEST_IP>:8000/health
curl -s --max-time 10 http://<DEST_IP>:8000/records
```

Then write one record from the source, through the TGW:

```bash
curl -s --max-time 10 -X POST http://<DEST_IP>:8000/records \
  -H 'Content-Type: application/json' \
  -d '{"name":"delta-widget","category":"synthetic"}'
```

Re-read the records and confirm the count is now **4**.

### 8.9 Restart and prove persistence

In the **destination** session:

```bash
PID=$(cat /home/ssm-user/dce-demo/app.pid)
kill "$PID"; sleep 2
nohup python3 app.py > app.log 2>&1 &
echo $! > app.pid
```

Re-read from the source:

```bash
curl -s --max-time 10 http://<DEST_IP>:8000/records
```

Wait for `curl --fail http://127.0.0.1:8000/health` to succeed on the destination after restart.
The delta record must still be there (count **4**). This proves the data moved with the
application, which is the point of the lab.

---

## Phase 9 — Negative routing test (controlled configuration change)

Do **not** delete or hand-edit a route in the console. Change the CodeCommit network
configuration so the change is reviewed, deployed by the pipeline, and reversible by commit.

1. In **CodeCommit → configuration repository → `main` → `network-config.yaml`**, find the
   **destination** VPC `DCE-POC-VPC` (`10.20.0.0/16`) and the route/entry that points
   `DCE-POC-RT-APP-A` at `10.10.0.0/16` via the TGW (route name `nameToSource`). Record the
   exact block and its line numbers.
2. **Remove only that named route** (leave `routes: []` if it was the only entry) for the destination VPC's `APP-A` subnet. Change nothing
   else: no CIDR edits, no other subnet, no source VPC change, no global route table.
3. Commit with a clear message (for example `remove dest APP-A route to 10.10.0.0/16 for
   negative test`). Note the new commit ID.
4. Run the pipeline as in 05 D3: **Release change**, review the diff against the previous
   commit, approve, wait for full success.
5. First confirm the deployed destination APP-A route is actually absent in VPC → Route tables.
   LZA may retain removed resources; if the route remains, record a blocked test, not a pass.
   **Verify the negative result.** In the source session:

```bash
set +e
curl --fail --show-error --connect-timeout 5 --max-time 10 http://<DEST_IP>:8000/health
DCE_CURL_STATUS=$?
printf 'curl exit code: %s\n' "$DCE_CURL_STATUS"
set -e
```

The `curl` must fail with a **new TCP timeout** (exit code 28), not a fast refusal — a
refusal would mean something else is answering.

6. **Restore exactly.** Re-add the identical route block at the same place in
   `network-config.yaml`, commit, run the pipeline, wait for success. Then re-run the
   `curl` from step 5 and confirm `/health` returns `{"status": "ok", ...}` again.
7. Confirm the **SSM sessions in both instances stayed up** throughout — removing a data route
   must not affect the SSM channel, which uses the instance's own VPC endpoints.
8. No production changes, no global route changes: only the one named destination `APP-A`
   route was touched, and it is now back to its original value.

---

## Phase 10 — Preventive control: SCP denying CreateUser

1. Complete **05a Stage 5**. The source file is
   [service-control-policies/dce-poc-deny-create-user.json](poc-config/service-control-policies/dce-poc-deny-create-user.json);
   upload it to that exact relative path in CodeCommit. The organization fragment attaches
   it to Non-Production. The separate security fragment deploys the **Config rule**, not the SCP.
2. Verify the policy target and wait for the pipeline to succeed. Keep the existing
   FullAWSAccess/Control Tower policies; do not replace them.
3. In **NonProduction**, sign in through the lab administrator permission set and open
   **CloudShell** (normal regional environment). Verify identity, then attempt:
```bash
aws sts get-caller-identity
aws iam create-user --user-name DCE-POC-DeniedUser
```
4. Expect **AccessDenied with an explicit SCP denial**. A generic denial could be an IAM
   issue, so also capture the applied SCP and the administrator's underlying permission.
   SCPs do not restrict Management: do not run the test there.
5. IAM → Users: verify `DCE-POC-DeniedUser` is absent. If it exists, the test failed:
   remove only this just-created, credential-less test user and investigate the policy.
6. Capture the CloudTrail `CreateUser` event and denial. IAM is global; inspect Event
   history in **us-east-1** if needed. Phase 12 proves central delivery separately.

---

## Phase 11 — Detective control: mandatory tag on EC2

1. In **NonProduction / London → AWS Config → Rules**, open the rule deployed by
   [07-controls-security.fragment.yaml](poc-config/07-controls-security.fragment.yaml).
   It uses AWS managed **REQUIRED_TAGS**, scoped to EC2 instances with parameter
   `tag1Key: Project`. **Do not create another console custom rule.**
2. Verify the Control Tower-owned recorder is running and records EC2 instances. If
   absent/stopped, resolve through the baseline, not by creating a competing recorder.
3. First confirm the destination instance with `Project=DCE-POC` is **COMPLIANT**.
4. EC2 → Instances → select destination → Tags → **Manage tags** → remove only
   `Project` → Save. AWS Config → rule → resource evaluation: wait for **NON_COMPLIANT**.
5. Restore exactly `Project=DCE-POC`; wait for **COMPLIANT** again.
6. Save timestamps and resource ID for all three states. Evaluation is asynchronous;
   no results, NOT_APPLICABLE or an evaluation error is not a pass. Do not weaken a
   mandatory tag policy to force the test; if it prevents removal, record that blocker.

---

## Phase 12 — Central log evidence

1. In **Management → CloudTrail → Trails**, open the existing organization trail and
   record its S3 destination, organization ID and prefix. Do not create another trail.
2. Sign in to **LogArchive** (not Audit) → S3 → that actual bucket. Follow
   `<prefix>/AWSLogs/<organization-id>/<NonProduction-account-id>/CloudTrail/<region>/YYYY/MM/DD/`
   as present in your bucket.
3. Download a recent `.json.gz` object and inspect it locally. Match the destination
   account ID, event time and `CreateTags`/`DeleteTags` or `StartSession` event in London.
   For IAM `CreateUser`, inspect the global-service region path, commonly `us-east-1`.
4. Match a known test event/event ID to the actual S3 record. A recent unrelated object
   alone is not sufficient. Allow delivery delay; no matching event yet means pending.
5. CloudTrail Event History is a separate **90-day** account/Region view; it can help locate
   the event but does not prove delivery into central S3.

---

## Phase 13 — Test results, evidence and rollback

| # | Test | Expected result | Evidence to capture |
|---|---|---|---|
| T1 | Preflight tooling | `python3`, `curl`, `tar`, `sha256sum` all present | Session transcript |
| T2 | SSM sessions via interface endpoints | Session opens; no public IP | Session start time, endpoint list |
| T3 | Source app `GET /health`, `/records` | `ok`, count 3 | Curl output |
| T4 | Bundle SHA-256 source vs destination | Digests identical | Both digest strings |
| T5 | Data transfer over TGW | Archive downloaded via `<SOURCE_IP>:8001` | Curl output, TCP 8001 SG rule |
| T6 | Extracted record count | 3 synthetic records | sqlite3 output |
| T7 | Dest app reachable from source | `/health` returns `ok` | Curl output |
| T8 | `POST /records` through TGW | 201, count becomes 4 | Curl output |
| T9 | Restart persistence | count still 4 after restart | Curl output |
| T10 | Negative route test | curl TCP timeout (exit 28) | Curl output + commit IDs |
| T11 | Route restore | `/health` ok again | Curl output + commit ID |
| T12 | SCP `iam:CreateUser` in NonProd | AccessDenied; no user created | Console error + IAM user list |
| T13 | Config tag rule | NON_COMPLIANT then COMPLIANT | Rule evaluation states + timestamps |
| T14 | Central log | Recent S3 object for destination account | Bucket, prefix, object key, timestamp |

**Rollback / safe state after the lab:** the source application stays **stopped** (it must,
so the destination is the system of record), the transfer server may stay up until cleanup,
the destination app may keep running so the client can see it live, and **both SSM sessions
stay open** for the demonstration. No route, SCP, or Config rule is left in a broken state.

---

## Phase 14 — Cleanup

Clean up only the resources this lab created, in this order, and prefer LZA-managed removal
for anything in the configuration repository.

1. Record the exact IDs before deleting anything: both instance IDs, all four endpoint IDs, both
   instance SGs, both endpoint SGs, both IAM roles, the SCP attachment, the Config rule, and
   the demo commits in CodeCommit.
2. Save evidence and the synthetic database first. Stop the exact demo process PIDs after
   verifying their command lines; do not use broad process-kill or recursive-delete commands.
3. Delete the **EC2 instances** (both accounts), then the **instance profiles and roles**
   (both accounts).
4. Delete the **VPC endpoints** and their security groups (both VPCs). Note the interface
   endpoints remain billable until deleted.
5. Remove only the demo SCP definition/attachment and Config rule set through CodeCommit/LZA.
   Deploy and verify their actual removal; preserve all mandatory controls and central logs.
6. Restore any test route change first. If retiring the network too, follow 05a's dependency-
   ordered teardown; do not delete whole configuration files or assume missing YAML deletes resources.
7. **The Transit Gateway is retained** unless the 05a cleanup is also executed — the
   attachments from 05a remain. Removing the YAML does not guarantee resource deletion.
   Verify actual resource state and the **Bills** view afterwards.
8. **No guarantee of zero bills.** Deleted resources can incur charges for the remainder of
   the billing period; unused Elastic Block Storage volumes, TGW attachments, and interface
   endpoints are the usual residue. Report actual observed charges, not an estimate.

---

## Cost caveat

Incremental lab cost, all in eu-west-2:

- 2 × `t3.micro` EC2 instances (Linux) — small, but non-zero and time-based
- 2 × TGW attachments (one per VPC) — charged per attachment, per hour
- 4 × interface endpoint-AZ units (2 endpoints × 2 VPCs), each charged per AZ-hour
- 2 × 8 GiB encrypted gp3 volumes (billed until deleted)
- CloudTrail S3 log delivery, Config evaluations, and GuardDuty/Security Hub already in the
  baseline — data volume dependent

Actual costs depend on duration, data volume and baseline settings; no fixed ranking or quote is assumed.

---

## Limitations

- This lab is **source-reviewed, not AWS-tested**. No command, console path, or result in
  this document has been executed against a live AWS account. Every expected result above is
  a **hypothesis to be tested and recorded**, not a claimed result.
- Nothing here has been validated by AWS or by a DCE reviewer.
- The app is a synthetic demonstration; no real or customer data is involved, and the data
  set is three made-up rows.
- No on-premises or server rehosting is demonstrated — only application + data rehost
  across accounts and VPCs over the Transit Gateway.
- No NAT, no internet egress path, and no S3 staging bucket are used for the transfer; the
  transfer runs host-to-host over the TGW on TCP 8001.
- The route negative test relies on the LZA pipeline applying and reverting the change. If
  the pipeline cannot express the route at that location, record that as a blocked test
  rather than editing routes by hand in the console.
- Dependency: this document assumes 05a has produced the two-VPC, two-AZ topology with
  bidirectional `/16` routes over `DCE-POC-TGW`. It depends on no file other than the
  links named above.

## Primary references

- [Private Systems Manager access](https://docs.aws.amazon.com/systems-manager/latest/userguide/setup-create-vpc.html)
- [AWS Config REQUIRED_TAGS](https://docs.aws.amazon.com/config/latest/developerguide/required-tags.html)
- [Preventive and detective controls](https://docs.aws.amazon.com/controltower/latest/userguide/how-controls-work.html)
