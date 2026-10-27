# 05 — LZA Pipeline Implementation Runbook (Console-First Lab)

**Final reading order:** this foundation guide → [05a network/security configuration](05a-poc-configuration-and-network-demo.md)
at Phase E → [05b migration and testing](05b-workload-migration-and-testing.md).
The approved demo now has two VPCs, two TGW attachments and two temporary EC2 instances.
Older tag-only proof below is one test, not the entire demonstration.

**Status: checked against the official v1.16.3 template and source; not yet executed in your AWS account.**
Follow the console steps and record each checkpoint. Console wording can change; if the
screen materially differs, capture the page and error before proceeding.

**Scope:** LZA foundation, generated pipelines and CodeCommit configuration. Start with one
fresh account; LZA first adds Audit and LogArchive, giving three accounts. Phase E's
[05a extension](05a-poc-configuration-and-network-demo.md) adds Network and NonProduction
(five accounts total), a TGW/private VPC attachment and London GuardDuty/Security Hub.
Home Region is London
(`eu-west-2`), with global-service access to `us-east-1`. Entra ID, Terraform, GitLab,
AFT, Direct Connect, VPN and central DNS remain talk-through topics.

**Companion documents (read-only):** [00](00-current-architecture-guide.md) ·
[01](01-demo-mandatory-requirements.md) · [03](03-presentation-talk-track.md) ·
[04](04-poc-scope-and-design.md)

---

## Table of contents

1. [Verified facts and pinned references](#1-verified-facts-and-pinned-references)
2. [Inputs to collect up front](#2-inputs-to-collect-up-front)
3. [Phase A — Account and identity prerequisites](#3-phase-a--account-and-identity-prerequisites)
4. [Phase B — GitHub token and Secrets Manager](#4-phase-b--github-token-and-secrets-manager)
5. [Phase C — Launch the installer stack](#5-phase-c--launch-the-installer-stack)
6. [Phase D — Monitor the deployment sequence](#6-phase-d--monitor-the-deployment-sequence)
7. [Phase E — Edit the generated configuration](#7-phase-e--edit-the-generated-configuration)
8. [Phase F — Release, approve, prove global tags](#8-phase-f--release-approve-prove-global-tags)
9. [Phase G — Enable IAM Identity Center explicitly](#9-phase-g--enable-iam-identity-center-explicitly)
10. [Phase H — Logging and security evidence](#10-phase-h--logging-and-security-evidence)
11. [Phase I — Cost visibility](#11-phase-i--cost-visibility)
12. [Phase J — Demo script, evidence, recovery](#12-phase-j--demo-script-evidence-recovery)
13. [Phase K — Cleanup](#13-phase-k--cleanup)
14. [Completion checklist and sources](#14-completion-checklist-and-sources)

---

## 1. Verified facts and pinned references

| Item | Value |
| --- | --- |
| Version | `v1.16.3`, verified 2026-10-26 from the template and `release/v1.16.3` |
| Installer template (pinned, HTTP 200) | `https://s3.amazonaws.com/solutions-reference/landing-zone-accelerator-on-aws/v1.16.3/AWSAccelerator-InstallerStack.template` |
| Launch step | https://docs.aws.amazon.com/solutions/latest/landing-zone-accelerator-on-aws/step-1.-launch-the-stack.html |
| Prerequisites | https://docs.aws.amazon.com/solutions/latest/landing-zone-accelerator-on-aws/prerequisites.html |
| Deployment step | https://docs.aws.amazon.com/solutions/latest/landing-zone-accelerator-on-aws/step-2.-await-initial-environment-deployment.html |
| Config step | https://docs.aws.amazon.com/solutions/latest/landing-zone-accelerator-on-aws/step-3.-update-the-configuration-files.html |
| Uninstall | https://docs.aws.amazon.com/solutions/latest/landing-zone-accelerator-on-aws/uninstall-the-solution.html |
| Source refs (verified) | `accelerator/lib/pipeline.ts`, `cdk-utils/lib/tagging-stacks.ts` on `release/v1.16.3` |
| Home region / stack / secret | `eu-west-2` / `AWSAccelerator-InstallerStack` / `accelerator/github-token` |
| CodeCommit availability | Reopened to new customers per AWS announcement 2025-11-24: https://aws.amazon.com/blogs/devops/aws-codecommit-returns-to-general-availability/ |

### Three repositories — keep them straight

1. **AWS public LZA source** `awslabs/landing-zone-accelerator-on-aws` @ `release/v1.16.3` —
   the *implementation* the installer runs, not your config.
2. **This local private docs repo** — runbooks and illustrative POC merge fragments;
   nothing here deploys automatically.
3. **Generated CodeCommit YAML repo** `aws-accelerator-config` @ `main` — *your* config.

The client also showed `aws/lza-universal-configuration`. We have screenshots, not their actual
YAML export or release details. This lab uses AWS's generated baseline and the same LZA/CodeCommit
pattern; it does not reproduce the client's exact configuration.

### Stacks you will see

- `AWSAccelerator-InstallerStack` — the console launcher. `CREATE_COMPLETE` means the
  **scaffold only** built.
- `AWSAccelerator-Installer` — the CodePipeline **created by** the installer stack.
- `AWSAccelerator-Pipeline` — the CodePipeline that **deploys** the landing zone.

---

## 2. Inputs to collect up front

Record these privately. Account emails must be supplied to AWS and appear in generated configuration.
Passwords, MFA details and tokens belong only in your password manager/Secrets Manager, never in Git.

| # | Input | Notes |
| --- | --- | --- |
| 1 | Lab account ID | Fresh standalone account |
| 2 | Root email | `ManagementAccountEmail` — the actual root/Organizations email, **not** an IAM user email |
| 3 | Log Archive email | Unique, unused AWS account email you control |
| 4 | Audit email | Another unique, unused AWS account email you control |
| 5 | Operator email | Receives the manual-approval SNS email |
| 6 | GitHub classic PAT | Scope `public_repo` only; expiry covers the whole lab |
| 7 | Region | `eu-west-2` (London) |
| 8 | Budget figure, e.g. `50 USD` | Illustrative; alerts are **not** a hard cap |

Management uses your existing account email. Only Audit and LogArchive need new addresses
not already associated with AWS accounts. Aliases work if you can receive mail at each address.

**Cost disclaimer.** AWS's LZA cost page shows a *sample* of **$430.22 USD/month in
us-east-1** for a sample sandbox. That is a documentation sample — **not** a quote,
minimum, or estimate for this London lab. [AWS cost example](https://docs.aws.amazon.com/solutions/latest/landing-zone-accelerator-on-aws/cost.html).
Choose a spending limit and retirement date; configure A3's alerts before launch.

---

## 3. Phase A — Account and identity prerequisites

### A1. Account and plan

1. Sign in as root. Top-right account menu → **Account**: record account ID and account email.
2. Open **Billing and Cost Management** and check your plan, credits and payment method.
3. Review the notice before creating an organization. AWS documents that a Free Tier account
   creating an organization upgrades to a paid plan and its Free Tier credits expire.
   Do not assume credits cover this lab. [AWS account-plan note](https://docs.aws.amazon.com/singlesignon/latest/userguide/enable-identity-center.html).

### A2. Root MFA

1. Top-right account menu → **Security credentials**.
2. Under **Multi-factor authentication (MFA)** choose **Assign MFA device**.
3. Name: `dce-root-mfa` → **Authenticator app → Next** → scan the QR code privately.
4. Enter the two consecutive codes requested → **Add MFA**. Do not create root access keys.

### A3. Budget — before deployment

1. Still as root: **Billing and Cost Management → Budgets → Create budget**.
2. **Customize (advanced) → Cost budget → Next**.
3. Name: `DCE-LZA-Lab`; period: **Monthly**; renewal: **Recurring**; method: **Fixed**.
4. Enter your chosen USD amount. `50` is only an illustrative alert threshold, not a cost estimate.
5. Leave cost filters empty so this management-account budget covers consolidated spend.
6. **Next → Add an alert threshold**: **Actual**, **50%**, your operator email.
7. Add **Actual 80%**, **Actual 100%**, and **Forecasted 100%** email alerts.
8. Continue without automated budget actions → review → **Create budget**.
9. Verify saved recipients. Alerts are delayed notifications, not spending caps.

### A4. Temporary IAM administrator

Do not enable IAM Identity Center before the fresh LZA auto-install. Use a temporary console
IAM administrator, then replace this access after the landing zone is healthy.

1. **IAM → Users → Create user**. Name: `dce-poc-bootstrap-admin`.
2. If you created this user from the earlier guide, verify it rather than creating another.
3. Select **Provide user access to the AWS Management Console → I want to create an IAM user**.
4. Choose **Autogenerated password**; keep **Users must create a new password at next sign-in** selected → **Next**.
5. **Attach policies directly** → search/select **AdministratorAccess → Next → Create user**.
6. On **Retrieve password**, save the sign-in URL, username and temporary password privately.
7. **IAM → Users → dce-poc-bootstrap-admin → Security credentials → Assign MFA device**.
8. Name: `dce-bootstrap-mfa` → **Authenticator app → Next** → scan privately → enter two consecutive codes → **Add MFA**.
9. Open the saved IAM sign-in URL in a private browser window. Sign in, enter MFA and change the temporary password.
10. Confirm IAM opens and the account ID is correct. Sign out root; continue with this administrator.

**Checkpoint:** named administrator works with MFA and no access keys. Keep it until Phase G passes.

### A5. Organizations — without a manual Control Tower setup

1. Search **AWS Organizations** → **Create organization**.
2. Review the creation/billing notice → confirm **Create organization**. The console creates it with all features.
3. Your current account automatically becomes management; do not create a second management account.
4. Follow **Verify your email address** in the organization email, if requested.
5. **Organizations → Settings**: confirm **All features**. **AWS accounts**: expand Root; only your account should exist.
6. Do not create OUs/member accounts or enable trusted access under **Services** yet.
7. Open **Control Tower**: no landing zone should exist. Do not choose **Set up landing zone**.
8. Open **IAM Identity Center**: no instance should exist. Do not choose **Enable** yet.
9. In **IAM → Roles**, search for `AWSControlTowerAdmin`, `AWSControlTowerCloudTrailRole`,
   `AWSControlTowerStackSetRole` and `AWSControlTowerConfigAggregatorRoleForOrganizations`; none should be preset.
10. **Service Quotas → AWS services → AWS Organizations**: check the account-count quota permits at least three accounts.
11. Select London and open **CodeCommit** to confirm service access. Do not create a repository manually.

**Checkpoint:** verified email, all features, one account, no OUs, trusted services, prior landing zone or Identity Center instance.
An existing organization meeting these checks can be reused. If a check fails, record the state;
do not delete existing resources to force the clean-install path.

### A6. CodeBuild quota

1. Set Region to **Europe (London) eu-west-2**.
2. **Service Quotas → AWS services → AWS CodeBuild**.
3. Open **Concurrently running builds for Linux/Large environment**.
4. If the applied quota is below `3`, choose **Request increase at account-level**, enter `3` → **Request**.
5. Track **Quota request history** and wait until the increase is applied before launching LZA.

### A7. Global-service access

Keep `us-east-1` global-service API access allowed. Do not add an SCP or Control Tower Region-deny
rule blocking it. LZA can add this Region to governance while retaining London as home Region.
This does not demonstrate UK-only workload/data residency.

---

## 4. Phase B — GitHub token and Secrets Manager

### B1. GitHub classic token

1. GitHub avatar → **Settings → Developer settings → Personal access tokens → Tokens (classic)**.
2. **Generate new token → Generate new token (classic)**. Note: `lza-lab`; expiry covering the lab.
3. Select **public_repo** only. Do not select the broader **repo** or **delete_repo** scope.
4. **Generate token** → save it once in your password manager. Resolve account restrictions before proceeding.

### B2. Store the raw token

1. AWS console, London → **Secrets Manager → Store a new secret → Other type of secret**.
2. Select **Plaintext**, delete the entire sample text, and paste only the PAT.
3. Do not add a `token` key, JSON wrapper, quotes or spaces.
4. Encryption key: `aws/secretsmanager` → **Next**.
5. Secret name: `accelerator/github-token`; optional tag `Project=DCE-POC` → **Next**.
6. Leave automatic rotation off → **Next → Store**.

**Checkpoint:** exact secret name in London, rotation off. Never capture its value in evidence.

### B3. Pre-flight checklist

- [ ] Management email and the two unused shared-account emails are correct.
- [ ] Root and bootstrap administrator MFA work.
- [ ] Organizations clean-install checks passed; at least three accounts are permitted.
- [ ] CodeBuild Linux/Large applied concurrency quota is at least 3 in London.
- [ ] Secret exists in London and PAT expiry covers the lab.
- [ ] CodeCommit is accessible; no configuration repository has been created manually.
- [ ] Budget alerts are active and the retirement date is recorded.

---

## 5. Phase C — Launch the installer stack

### C1. Load the official template

1. Confirm the console Region is London.
2. **CloudFormation → Stacks → Create stack → With new resources (standard)**.
3. Choose **Choose an existing template**, then **Amazon S3 URL** under template source.
4. Paste this URL → **Next**:

```text
https://s3.amazonaws.com/solutions-reference/landing-zone-accelerator-on-aws/v1.16.3/AWSAccelerator-InstallerStack.template
```

**C2. Set the stack name AND every parameter on the SAME page.** On **Specify stack details** fill both the stack name and all parameters before clicking Next again.

| Parameter | Value |
| --- | --- |
| Stack name | `AWSAccelerator-InstallerStack` |
| RepositorySource | `github` (the AWS implementation source, not your config) |
| RepositoryOwner | `awslabs` |
| RepositoryName | `landing-zone-accelerator-on-aws` |
| RepositoryBranchName | `release/v1.16.3` |
| EnableApprovalStage | `Yes` |
| ApprovalStageNotifyEmailList | operator email (confirm the SNS mail arrives) |
| ManagementAccountEmail | actual root / Organizations email |
| LogArchiveAccountEmail | unique unused AWS email #2 |
| AuditAccountEmail | unique unused AWS email #3 |
| ControlTowerEnabled | `Yes` |
| AcceleratorPrefix | `AWSAccelerator` |
| EnableDiagnosticsPack | `Yes` |
| ConfigurationRepositoryLocation | `codecommit` |
| UseExistingConfigRepo | `No` |
| ExistingConfigRepositoryName | *(empty)* |
| ExistingConfigRepositoryBranchName | *(empty)* |
| ExistingConfigRepositoryOwner | *(empty)* |
| ConfigCodeConnectionArn | *(empty)* |

There is **no** `HomeRegion`, `DeploymentRegions`, or token-secret-name parameter. The
region is the console region (`eu-west-2`) and the secret name is fixed as
`accelerator/github-token`. Do not look for those fields.

### C3. Launch

1. **Next → Configure stack options**: leave role/default options unchanged; keep rollback enabled.
2. **Next → Review and create**: confirm parameters, email spelling and London Region.
3. Select the required IAM capability acknowledgement → **Submit**.
4. Open **Events** and refresh until `CREATE_COMPLETE`. This confirms only the installer scaffold.

### C4. If the stack fails

1. Open **Events**, find the first meaningful failed resource, and record its reason.
2. Wait for any rollback to finish. Do not create parallel installers.
3. An existing healthy stack can be updated; a `ROLLBACK_COMPLETE` initial stack cannot simply
   be updated. Inspect what it retained before planning a replacement. Do not delete the organization
   or accounts to retry. Pipeline-source token failures are handled in the pipeline, not by replacing the stack.

---

## 6. Phase D — Monitor the deployment sequence

Sequence: **installer scaffold → `AWSAccelerator-Installer` pipeline →
`AWSAccelerator-Pipeline`.** Monitor both. Do **not** wait for Control Tower before
running the pipeline — enrollment is driven *by* the pipeline and takes a long time.

**D1. Installer pipeline.** **CodePipeline** → `AWSAccelerator-Installer` → read stages in
order; record the **execution ID** and source commit. **Checkpoint:** healthy/successful.

**D2. Deployment pipeline and the approval stage.**
**CodePipeline** → `AWSAccelerator-Pipeline` → read the stage graph:

`Prepare` → `Accounts` → `Bootstrap` → **`Review` (approval)** → `Logging` →
`Organization` → `SecurityAudit` → `Deploy`

**Approval scope — read carefully.** The manual **Review/Approve** stage sits **after**
`Prepare`, `Accounts`, `Bootstrap` and **before** `Logging`, `Organization`,
`SecurityAudit`, `Deploy`. The gate therefore covers the later stages only — **not** every
change in the run. Never claim "all changes are gated": `Prepare`, `Accounts` and
`Bootstrap` execute without an approval action. **Expected:** the run parks at `Review`
with **Action Required**, which is normal with `EnableApprovalStage=Yes`.

**D3. Inspect, then approve.** Open the `Review` stage's `Approve` action. Follow its
review URL to the S3 diff artifacts for this execution (`Diffs/<execution-id>`). Read
the stack differences, accounts and regions; save evidence. Reject unexpected deletions,
replacements or unintended regions. Otherwise choose **Review / Approve**, add a short
reason and submit. There is no required Terraform plan or execution-name entry.

**D4. Run to completion.** Stages may take **hours**; real runtime is demo evidence — do
label edited waiting periods in a recording and retain execution timestamps. On failure:
the stage's CodeBuild log → CloudWatch Logs → and the
failing stack's CloudFormation **Events**. Fix the config (Phase E) and release again;
never release repeatedly while a run is active.

---

## 7. Phase E — Edit the generated configuration

**Expanded POC: do [05a — POC configuration and network demo](05a-poc-configuration-and-network-demo.md)
first.** It supplies the account, OU, network and security YAML changes in staged runs.
The steps below are the **final tag-change exercise only**, after those runs succeed;
they are no longer the whole of Phase E. Keep the generated baseline and merge only the
specified blocks. Do not replace all six configuration files with fragments.

**Scope of Phase E.** The LZA v1.16.3 foundation is already deployed and healthy (Phase D
run green). Phase E changes **one file only** — `global-config.yaml`. It does not
re-deploy the foundation, does not enable any service, and does not change any other
configuration file. Everything else in the repo stays exactly as generated.

**E1. Find the *config* repo, not the source repo.** **CodePipeline** →
`AWSAccelerator-Pipeline` → open the execution → find the action for the **configuration
source** (the CodeCommit-source action, labelled **Configuration**) → read the repository
name and branch from that action. Expected: `aws-accelerator-config`, branch `main` —
older docs say `aws-accelerator-configuration`, but the v1.16.3 template says
`aws-accelerator-config`; trust the action, not the docs. Do **not** create the repo
manually and do **not** switch source providers mid-install.

**Checkpoint:** the configuration source action shows repository `aws-accelerator-config`
on branch `main`.
**Stop condition:** if the action names a different repository or branch, stop and
reconcile against the action before touching any file.

**E2. The six configuration files — inventory and action.** These are the files the
installer generated in the config repository.

| File | Purpose | Action in this lab |
|---|---|---|
| `global-config.yaml` | Global landing-zone settings, **including the root `tags` list** that drives global tagging | **EDIT — the only file changed in Phase E** |
| `accounts-config.yaml` | Member accounts and their settings (account name/email, OU placement) | **Unchanged** |
| `iam-config.yaml` | IAM policy, role and identity configuration | **Unchanged** |
| `network-config.yaml` | Network baseline (VPC CIDRs, subnets, DNS) | **Unchanged** |
| `organization-config.yaml` | OUs and the organization hierarchy | **Unchanged** |
| `security-config.yaml` | Security service configuration | **Unchanged** |

**Checkpoint:** only `global-config.yaml` is opened for editing; the other five are
treated as read-only for this phase.
**Stop condition:** if any step below would require editing a second file, stop — that is
outside Phase E scope.

**E3. Back up before you edit.**

1. **CodeCommit** → `aws-accelerator-config` → branch `main` → **Commits** → note the
   current **commit ID** at the top of the list. This is your rollback point (E8).
2. Return to **Code**, select `main`, and open `global-config.yaml`. Copy the complete
   file content (not page navigation or line numbers) into a local text editor and save
   it as `global-config.before-demo.yaml`. Save this **original content locally**, outside the repo working
   tree, stored securely — the file carries account emails and organization settings, so
   treat it as internal data, not a file to paste into chat or commit elsewhere. Keep the
   local copy and the commit ID together, and note which commit ID the copy came from.

**Checkpoint:** commit ID recorded **and** a local copy of the pre-edit
`global-config.yaml` saved.
**Stop condition:** no backup yet — do not start editing.

**E4. Edit the root `tags` list in `global-config.yaml`.** CodeCommit →
`aws-accelerator-config` → `main` → open `global-config.yaml` → **Edit**. Find the
**root-level** `tags:` list — a top-level key of the file, not a nested block inside an
account, OU, or other section. Check which of the three cases you have before editing.

*Case A — there is no `tags` key at root.* At the end of the file, start a new line
with `tags:` at column 1 (no leading spaces). Use spaces, not tabs. Add this block and
change nothing else:

```yaml
tags:
  - key: Project
    value: DCE-POC
  - key: DemoRevision
    value: '1'
```

*Case B — `tags: []` (an empty list).* Replace the empty list with the same block:

```yaml
tags:
  - key: Project
    value: DCE-POC
  - key: DemoRevision
    value: '1'
```

*Case C — `tags:` already contains entries.* **Keep every existing entry** and append the
two new ones. Example — if the generated file already contains:

```yaml
tags:
  - key: Owner
    value: platform-team
```

then the result is:

```yaml
tags:
  - key: Owner
    value: platform-team
  - key: Project
    value: DCE-POC
  - key: DemoRevision
    value: '1'
```

The `Owner: platform-team` entry above is **illustrative only** — it shows the shape of a
pre-existing tag. It is **not** a value to copy: never add an `Owner` entry, and never
copy `platform-team` into the file. Use whatever entries your generated file actually
contains.

Rules for the edit:

- **Exactly one root `tags:` block.** Never add a second `tags:` key, and never add a
  duplicate `Project` or `DemoRevision` entry inside the list.
- If `Project` or `DemoRevision` **already exists** at root, **stop and review it before
  overwriting** — the existing value may be meaningful. Record the old value, then
  replace only that single entry, leaving key order and all other entries intact.
- Quote numeric-looking values (`'1'`) so they stay strings.
- **Preserve the rest of the file byte-for-byte** — do not reformat, re-indent, reorder,
  or replace the whole file. Do not invent OU or IAM field names: the generated
  accounts/OUs/regions in the file are the ground truth of what exists.

**Checkpoint:** one root `tags:` list containing `Project = DCE-POC` and
`DemoRevision = '1'`, every pre-existing entry retained, remainder of the file unchanged.
**Stop condition:** if the edit touches any key other than the root `tags` list, undo it
and re-edit.

**E5. Commit, then verify the diff.** In the CodeCommit edit view, enter the **commit
author name and email** (the operator's own name and email), and a commit message such as:

```text
Add global tags for demo revision 1
```

→ **Commit changes**. Then verify before releasing: **CodeCommit** →
`aws-accelerator-config` → **Commits** → open your new commit → the **Changes** view
must show **only `global-config.yaml`**, and the diff inside it must show only the
`tags` block. If any other file, or any other hunk, appears — stop and fix the edit
before releasing.

**Checkpoint:** new commit on `main`; diff shows `global-config.yaml` only, `tags` block
only.

*Process note:* committing directly to `main` is acceptable **only** because this is a
disposable lab with a mandatory manual approval stage — the `Review` stage that follows
Prepare / Accounts / Bootstrap. It is **not** independent PR review and must not be
presented as such. Approval gates the stages after Review, not Prepare / Accounts /
Bootstrap. This single-operator lab does not demonstrate separation of duties or prove
compliance.

**E6. Revision 2 — prepare the YAML, do not commit it yet.** The second revision used in
Phase F4 is the same block with `DemoRevision` changed to `'2'`:

```yaml
tags:
  - key: Project
    value: DCE-POC
  - key: DemoRevision
    value: '2'
```

Keep this snippet as a note. **Do not commit or release it yet** — revision 1 must first
be released, approved, run to completion and verified on a downstream resource (Phase F3)
before revision 2 is committed. Committing early risks shipping the wrong revision to
the demo and invalidating the recorded artefact.

When you reach **F4**, perform these steps:

1. CodeCommit → repository → **Code** → `main` → `global-config.yaml` → **Edit**.
2. Under the existing `key: DemoRevision`, change only `value: '1'` to `value: '2'`.
   Keep `Project` and every other existing tag unchanged; do not paste over the whole list.
3. Enter your author name/email and message `Update demo revision from 1 to 2` →
   **Commit changes**. Open the new commit and verify the diff changes only that value.
4. Record the new commit ID, then follow **F1–F3** again. Verify the execution uses this
   commit and the same downstream resource now shows `DemoRevision = 2`.

**E7. What the tags will and will not do.** Global tags are applied to **taggable
resources** only. They are **not** guaranteed as **stack-level** tags on generated
CloudFormation stacks. Two source references govern this on `release/v1.16.3`:
`accelerator/lib/pipeline.ts` (stage/approval structure) and
`cdk-utils/lib/tagging-stacks.ts` (tag propagation). The proof of tagging is therefore a
**resource-level** proof — see Phase F3. This demo shows configuration propagation; make
**no** security, governance or compliance claim from it.

**E8. Rollback.** If a released revision fails (YAML parse error, a bad tag value, or a
pipeline run that fails at the configuration stage), roll back by configuration, not by
git alone:

1. **CodeCommit** → `aws-accelerator-config` → `main` → open `global-config.yaml` →
   **Edit**.
2. Restore the **original `tags` block exactly** as captured in E3. If the original file
   had **no** root `tags` block, **remove only the block you added** — do not delete or
   alter anything else. If the original file **had** entries, restore those exact
   entries; remove only the entries you added.
3. **Preserve every other change** you want to keep — the rollback edit is minimal and
   targeted at the `tags` list.
4. **Commit** with a message such as `Revert global tags to pre-edit state`, then
   **Release change** and **Approve** the `Review` stage as in Phase F1/F2, and **verify**
   the run completes and the pipeline is healthy again. Reopen the same resource's Tags
   tab to confirm its tags match the original state; a green run alone is not that proof.

**Git alone is not a rollback.** Reverting a commit in git changes the repository only;
release and successfully run the pipeline to apply the restored configuration. Some
stages run before approval, and a failed run can leave partial changes. Inspect the
execution and resource state rather than assuming a failed run changed nothing.

**E9. Phase E checkpoints and stop conditions.**

| Checkpoint | Expected |
|---|---|
| E1 | Configuration source action = `aws-accelerator-config` / `main` |
| E2 | Only `global-config.yaml` is open for edit; other five files untouched |
| E3 | Commit ID noted; local copy of the pre-edit `global-config.yaml` saved securely |
| E4 | One root `tags:` list — `Project = DCE-POC`, `DemoRevision = '1'`, existing entries preserved |
| E5 | Commit on `main`; diff shows `global-config.yaml` only |

**Stop conditions (any one halts Phase E):** a second file needs editing; the diff shows
unexpected files or hunks; `Project` or `DemoRevision` already exists and has not been
reviewed; a second root `tags:` key or a duplicate tag key would be introduced; any
service would need to be enabled; the edit would touch anything other than the root
`tags` list.

References: [AWS CodeCommit console editing](https://docs.aws.amazon.com/codecommit/latest/userguide/how-to-edit-file.html)
and [LZA v1.16.3 global configuration schema](https://github.com/awslabs/landing-zone-accelerator-on-aws/blob/release/v1.16.3/source/packages/%40aws-accelerator/config/lib/models/global-config.ts).

---

## 8. Phase F — Release, approve, prove global tags

**F1. CodeCommit trigger is NONE — Release change is required.** A commit to `main` does
**not** start a deployment. **CodePipeline** → `AWSAccelerator-Pipeline` → **Release
change** → confirm the release if prompted. First verify `main` still points to your
intended commit. If a run is already active, do not release again. **Checkpoint:** open
the new execution's source revisions and confirm the **Configuration** action shows
your commit ID. Do not assume a commit-selection dialog will appear.

**F2. Approve.** The run parks at **`Review`** (after Prepare/Accounts/Bootstrap, before
Logging/Organization/SecurityAudit/Deploy). Inspect the change summary, then **Approve**
as in D3. **Checkpoint:** run completes successfully.

**F3. Prove the global tags on a real downstream resource.** Never use the installer's
or the pipeline's own key/role — those are the solution's own KMS keys, unrelated to your
global tag configuration.

1. **CloudFormation** → the region the pipeline deployed in → find the **downstream** stack
   created by the `Logging` stage (e.g. the `AWSAccelerator-Key` / KMS key stack).
2. Stack → **Resources** → locate the KMS key resource → note its **Physical resource
   ID** (a key UUID or ARN). Do not rely on the logical resource ID.
3. **KMS** → **Customer managed keys** → open that key by ID → **Tags** tab.
4. **Expected:** `Project = DCE-POC` and `DemoRevision = 1`.
5. **Pass criteria:** tags visible on the **KMS key**, identified by its physical ID from
   the downstream stack's Resources list. Screenshot the KMS Tags tab beside that list.
6. **Stop condition:** if no tags appear, record "global tags not observed at resource
   level" and check `cdk-utils/lib/tagging-stacks.ts` before claiming success. A missing
   stack-level tag is **not** itself a defect.

**F4. Second revision.** Change `DemoRevision` `'1'` → `'2'` → commit → release → approve
→ re-check the KMS **Tags** tab: `DemoRevision` should now read `2`. This is the recorded
demo artefact.

---

## 9. Phase G — Enable IAM Identity Center explicitly

**G1. Why this is separate.** The **generated** Control Tower landing-zone configuration
sets `landingZone.security.enableIdentityCenterAccess` to **false**. A green pipeline
therefore does **not** mean Identity Center is on. The lab enables it deliberately,
**after** the first healthy pipeline run, so the run stays deterministic.

**G2. Enable on the organization instance.** **IAM Identity Center** → check the
**identity source** in **Settings** first; if it points at an external IdP (Entra ID or
other) do **not** reconfigure it — Entra ID is talk-through only in this lab; use the
existing directory. If no instance exists, choose **Enable IAM Identity Center** on the
**organization instance** (not a standalone instance). Configure: **region
`eu-west-2` (London) — a single region** and **multi-account permissions ON**.
**Checkpoint:** instance enabled in London with multi-account permissions on. **Stop
condition:** if the console offers a *new* standalone instance while an organization
instance exists, cancel and use the organization instance.

**G3. Local operator and account access.** For this lab's local Identity Center directory:

1. **IAM Identity Center → Users → Add user**. Enter `lab-operator`, your real email,
   first/last name and display name; choose an invitation email, then **Next → Add user**.
2. **Groups → Create group**. Name it `Lab-Administrators`, select the user and create it.
3. **Settings → Authentication → Multi-factor authentication → Configure**. Require MFA
   at every sign-in and require users without an MFA device to register one. Save.
4. **Permission sets → Create permission set → Predefined permission set**. Select
   **AdministratorAccess**, continue with a one-hour session duration, review and create.
5. **AWS accounts**: select Management, Audit and LogArchive (plus Network and
   NonProduction when 05a has created them) → **Assign users or groups** → **Groups** →
   `Lab-Administrators` → **Next** → select `AdministratorAccess` → review → **Submit**.

**Checkpoint:** assignments provision successfully for all deployed lab accounts.
AdministratorAccess is deliberately broad for this disposable lab; do not claim least privilege.

**G4. Portal test.** Sign in to the Identity Center **portal** as `lab-operator` with MFA
and open every assigned lab account. **Checkpoint:** portal sign-in works for all five after 05a,
including the member accounts (needed for Phase H evidence).

**G5. Retire the bootstrap user carefully.** Only after G4 passes. **IAM** →
**Users → dce-poc-bootstrap-admin → Security credentials → Console sign-in → Manage
console access → Disable → Apply**. Before deleting any IAM user, check for access keys, policies or owned
resources. **Checkpoint:** bootstrap console access off, Identity Center path proven.

---

## 10. Phase H — Logging and security evidence

**H1. CloudTrail — actual destination.** **CloudTrail** → **Trails** → open the trail LZA
created → open **Details** / **Storage location** and record the **actual** S3 bucket URL
and prefix. **Event history** is only a local query view — it is **not** proof of
centralized delivery. Do **not** create a second trail.

**H2. Prove delivery.** Via the Identity Center portal switch to the **log archive**
account → **S3** → that bucket → the prefix LZA wrote to → look for recent objects with
recent `Last modified`. **Pass criteria:** at least one recent object in the log archive
account's bucket; screenshot the object list.

**H3. Security services — report what is actually enabled.** The initial LZA source sets
**GuardDuty: false** and **AWS Security Hub: false**, so a green pipeline is **not**
evidence either is on. After 05a's security deployment, both should be enabled in London;
use 05a's administrator/member verification checkpoints. Check the relevant consoles and
record the observed on/off state honestly. Do not click **Enable** in a way that conflicts
with LZA ownership of the account config — if you add a schema phase, agree it with the
main reviewer first and do it through the configuration file. Any GuardDuty findings you
generate must be labelled **synthetic**; an empty findings list does **not** prove the
integration works.

---

## 11. Phase I — Cost visibility

1. **Billing and Cost Management** → **Budgets** → **Create budget** → scope this account
   with **no filters** → name `DCE-LZA-Lab` → amount e.g. `50 USD` → monthly → add the
   operator email for actual and forecast alerts.
2. A budget alert is a **notification, not a hard cap** — it does not stop spend and is
   not a guarantee. There is no free-tier guarantee for this lab.
3. **Ongoing cost drivers after the pipeline stops:** KMS keys and rotation; S3 log
   storage in the log archive account; CloudTrail and any enabled GuardDuty / Security
   Hub; AWS Config evaluations; and the TGW attachment added in 05a. Accounts and Control
   Tower do not themselves have a base service fee. List the underlying services in the
   demo script.

---

## 12. Phase J — Demo script, evidence, recovery

**J1. Demo script (8–10 minutes)**

1. **00:00–01:00** Problem statement ([01](01-demo-mandatory-requirements.md)).
2. **01:00–02:30** What LZA generates: management, audit, log archive, OUs, Control Tower
   governance ([00](00-current-architecture-guide.md)).
3. **02:30–04:00** Pipeline stage graph, showing `Review` between `Bootstrap` and
   `Logging`.
4. **04:00–05:30** Config: `global-config.yaml` `tags` array, the commit, the manual
   **Release change** (CodeCommit trigger is NONE).
5. **05:30–07:30** Tag proof: KMS key physical ID from the downstream stack's
   **Resources** → KMS **Tags** tab showing `Project` and `DemoRevision=2`.
6. **07:30–08:30** Identity Center: org instance, `eu-west-2`, multi-account ON, group +
   permission set + three assignments, portal sign-in.
7. **08:30–09:30** Logging: CloudTrail **Details** → S3 destination → log archive objects.
8. **09:30–10:00** Honest limits: show actual security deployment status, budget alerts
   are not caps, real runs take hours.

**J2. Evidence checklist**

| Evidence file | Content | Pass criteria |
| --- | --- | --- |
| `01-org-all-features.png` | Organizations all features, management member | "All features" + management account shown |
| `02-installer-stack-complete.png` | `AWSAccelerator-InstallerStack` | `CREATE_COMPLETE`, stack ID legible |
| `03-installer-pipeline-success.png` | `AWSAccelerator-Installer` execution | Success state + execution ID |
| `04-pipeline-stage-graph.png` | `AWSAccelerator-Pipeline` graph | `Review` between `Bootstrap` and `Logging` |
| `05-review-change-summary.png` | Change summary before approving | No unexpected deletions/replacements |
| `06-config-repo-commits.txt` | Commit IDs from `aws-accelerator-config` | Revision 1 and 2 IDs |
| `07-release-change-evidence.png` | **Release change** in CodePipeline | Source action shows the intended commit |
| `08-kms-key-resource-id.png` | Downstream stack **Resources** → KMS physical ID | `key-…` ID legible |
| `09-kms-tags.png` | KMS key **Tags** tab | `Project=DCE-POC`, `DemoRevision` present |
| `10-identity-center-settings.png` | Org instance, London, multi-account ON | Region and toggle visible |
| `11-portal-signin-accounts.png` | Portal with three accounts | Management, audit, log archive listed |
| `12-cloudtrail-s3-destination.png` | CloudTrail **Details** S3 destination | Actual bucket URL legible |
| `13-log-archive-objects.png` | Recent objects in log archive bucket | Recent `Last modified` timestamps |
| `14-security-services-state.png` | GuardDuty / Security Hub states | Observed state recorded honestly |
| `15-budget-config.png` | Budget, no filters, notifications | Scope and amount visible |
| `16-catalog-logs.txt` | Execution IDs, commit IDs, stack IDs | All identifiers recorded |

**J3. Recovery playbook**

| Symptom | Action |
| --- | --- |
| YAML invalid, run fails at Prepare | Restore the previous working content (commit ID from E3), commit, release again |
| GitHub token expired | Update the **same** secret `accelerator/github-token` (B2) with a new PAT, then retry the source stage |
| Run sits at `Review` | Expected with `EnableApprovalStage=Yes`; approve deliberately — do not delete the run |
| CodeBuild concurrency error | Raise the CodeBuild quota (A5), then re-release |
| Organization email mismatch | `ManagementAccountEmail` must be the actual root/Organizations email — fix the value, not the user |
| Wrong region | Do not improvise; re-check the pinned template parameters (C2) |
| Pre-existing accounts/OUs/resources conflict | **Do not delete anything**; capture the error, use AWS Support |
| Control Tower enrollment fails | Capture the failing stack's CloudFormation **Events**, open a support case |
| "Undo" the commit | A git revert does **not** undo created accounts or deployed resources; use the official uninstall flow |

**J4. Discipline.** Serialize changes — one config change and one run at a time; record
the old value beside every new value; never release during an active run; screenshot
before you change or delete anything.

---

## 13. Phase K — Cleanup

**K1. Decide.** Keep the lab if you still need to record or demo — costs continue. To
retire, follow the official uninstall flow:
https://docs.aws.amazon.com/solutions/latest/landing-zone-accelerator-on-aws/uninstall-the-solution.html

**K2. Inventory before deleting anything.** List every account (management, audit, log
archive, any member accounts) with IDs and emails; every region with resources; every
CloudFormation stack with ID and status; every S3 bucket with its region. Export all
evidence (screenshots, logs, commit IDs) and a copy of the final YAML. **Checkpoint:**
inventory complete.

**K3. Reverse deployment order.** Follow the official uninstall document's order and
dependency graph exactly. Retained buckets are intentionally left behind — clean them
deliberately; there is no wildcard "delete all" step, and blind bulk deletion can destroy
the log evidence you need. Control Tower decommission is a **separate** operation from
LZA uninstall, and account closure is **not** automatic. Use the official Control Tower
decommission guide for that portion:
[Decommission a landing zone](https://docs.aws.amazon.com/controltower/latest/userguide/decommission-landing-zone.html).
Complete 05a's added-resource cleanup checks as well; stopping the pipeline stops no
ongoing service charges.

---

## 14. Completion checklist and sources

1. **Deployment evidence** — complete 05a's network/security checks as well as the
   foundation, identity, logging and tag checks here. No AWS execution has been tested by
   the document author; record actual results before presenting success.
2. **Exact KMS stack name** — the downstream stack may be `AWSAccelerator-Key` or
   similar. Read the actual name in CloudFormation rather than trusting this document.
3. **Tag propagation edge cases** — `cdk-utils/lib/tagging-stacks.ts` on
   `release/v1.16.3` governs which resources receive global tags. Confirm the supported
   resource set before claiming coverage beyond the KMS key proof.
4. **Approval stage position** — the `Review` ordering stated in D2 is based on
   `accelerator/lib/pipeline.ts` and the observed graph; re-verify against your run's
   graph, and show the recorded order in the demo.
5. **`enableIdentityCenterAccess` value** — stated as `false`; confirm the generated
   value in your account's config before saying it in the demo.
6. **Cost** — $430.22 USD/month is AWS's published sample for a sample sandbox in
   us-east-1. Never present it as a London estimate.
