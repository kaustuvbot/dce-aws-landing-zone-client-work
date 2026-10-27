# 05a — POC Configuration and Network Demo (Five-Account, London)

## Scope (approved)

- Five accounts: **Management, LogArchive, Audit, Network, NonProduction**. No Sandbox account.
- New network/security resources: London (`eu-west-2`) only. Preserve the foundation's
  global-service access and generated enabled Regions, including `us-east-1` where present.
  Network: one TGW `DCE-POC-TGW`, RAM-shared to NonProduction only, **two private VPCs and
  two attachments**. The Network account hosts both the TGW and the temporary source VPC
  `DCE-POC-SOURCE-VPC` (`10.10.0.0/16`); NonProduction hosts the target `DCE-POC-VPC`
  (`10.20.0.0/16`) and is the only RAM share consumer. Each VPC has two application and two
  TGW subnets across two AZs.
  Security: Audit account, GuardDuty, Security Hub.
- Baseline required: the existing generated three-account configuration must exist before this demo.
- Account quota: at least 5; Network and NonProduction will be **created**, not assigned
  from unused accounts. Supply two unused, distinct AWS root email addresses you control.
- Budget: confirm the POC budget before starting; the old baseline estimate is invalid.

## Fragments to merge (not replacements)
Merge the supplied fields only into the matching existing LZA YAML files. They are **merge fragments**,
not drop-in replacement files:

- [poc-config/01-organization.fragment.yaml](poc-config/01-organization.fragment.yaml)
- [poc-config/02-accounts.fragment.yaml](poc-config/02-accounts.fragment.yaml)
- [poc-config/03-network.fragment.yaml](poc-config/03-network.fragment.yaml)
- [poc-config/04-security.fragment.yaml](poc-config/04-security.fragment.yaml)
- [poc-config/05-global-tags.fragment.yaml](poc-config/05-global-tags.fragment.yaml)
- [poc-config/06-controls-organization.fragment.yaml](poc-config/06-controls-organization.fragment.yaml)
- [poc-config/07-controls-security.fragment.yaml](poc-config/07-controls-security.fragment.yaml)
- [SCP policy JSON](poc-config/service-control-policies/dce-poc-deny-create-user.json)

## Out of scope

No NAT, IGW, real on-prem connectivity, production shared services, central DNS, Entra ID,
Account Factory for Terraform, Terraform and GitLab. `iam-config.yaml` is unchanged;
operator access is assigned through Identity Center. **05b** adds two EC2 instances,
their roles/security groups and four SSM interface endpoints as temporary, console-built
workload resources. LZA continues to own VPC/TGW routing; do not manage the same resource
through both methods. No five-year retention claim is made. Hosting a source in Network
is a disposable simulation, not the proposed production placement for legacy applications.

## Console sequence

Start after **05 Phase D succeeds**, before the Phase E tag exercise. Management account,
London console, `aws-accelerator-config`, branch `main`; trust the pipeline's actual
Configuration action if its repository name differs. Keep Control Tower auto-enrollment
enabled and generated mandatory-account names unchanged. Never upload the `.fragment.yaml`
filenames as extra LZA configuration files: edit the existing target files below.

| Fragment | Target file / merge location |
|---|---|
| 01 | `organization-config.yaml` → append missing entries to `organizationalUnits`; preserve Security and all policies |
| 02 | `accounts-config.yaml` → append to `workloadAccounts`; preserve `mandatoryAccounts` |
| 03 | `network-config.yaml` → fill `transitGateways` and `vpcs`; this walkthrough requires both lists empty/absent |
| 04 | `security-config.yaml` → merge the shown fields inside `centralSecurityServices`, never replace that whole object |
| 05 | `global-config.yaml` → merge `tags` as described in 05 Phase E |
| 06 | `organization-config.yaml` → append the SCP definition to `serviceControlPolicies`; preserve all existing policies |
| 07 | `security-config.yaml` → append the rule set under `awsConfig.ruleSets`; preserve the Control Tower-owned recorder |

1. **Back up first.** In CodeCommit, back up the `main` branch and the original six configuration
   files. Record the current commit ID before any edit.
2. **Edit and merge.** CodeCommit → Repositories → configuration repository → **Code** →
   `main` → target file → **Edit**. Paste only the supplied fragment fields, preserve all
   other existing data, and append to existing lists rather than replacing or duplicating entries.
3. **Commit.** Set author and email, write a commit message naming the fragment, then `Commit changes`.
4. **Review the diff.** Open Commits, compare the new commit against the recorded baseline commit ID, and
   confirm only the intended fragment fields changed.
5. **Stage 1 — org + accounts.** Commit *both* the organization and accounts fragments before running
   the Release change. Replace both `.invalid` email placeholders with your real unused
   addresses **before committing**. Keep `warm: false`. Reuse an existing matching OU;
   stop if either account name already exists. CodePipeline → `AWSAccelerator-Pipeline`
   → **Release change** → confirm. Inspect/approve Review as in 05 D3; wait for full success.
   Organizations → AWS accounts: verify Network under Infrastructure and NonProduction
   under Non-Production. Control Tower → Organization: verify both OUs registered and
   both accounts enrolled, with no pending/failed status.
6. **Stage 1 access.** Follow **05 Phase G** to create/test the local operator if needed.
   Identity Center → AWS accounts → select Network and NonProduction → **Assign users or
   groups** → `Lab-Administrators` → `AdministratorAccess` → review → Submit. Test both
   accounts through the access portal; record their account IDs.
7. **Stage 2 — network.** Merge the network fragment and run one deployment. Verify: TGW created;
   Network RAM share to NonProduction exists; both VPCs/attachments are available; both TGW
   associations exist; `10.10.0.0/16` and `10.20.0.0/16` are propagated. The source VPC is
   in the Network account, so its attachment is same-account and needs no RAM share; only
   the NonProduction attachment consumes the share. Stop if the generated network lists
   already contain resources or these CIDRs conflict; do not overwrite them. Leave all
   other network keys unchanged. LZA's Organizations stack enables RAM organization
   sharing; if sharing is unavailable, inspect that stack rather than bypassing it manually.
   In **Network / London**, VPC → Transit gateways → `DCE-POC-TGW`; RAM → Shared by me →
   verify only NonProduction is a principal. VPC → Transit gateway route tables →
   `DCE-POC-RT` → Associations, Propagations and Routes: verify both attachments and active
   propagated CIDRs. In **NonProduction / London**, VPC → Your VPCs →
   `DCE-POC-VPC`; verify four subnets, two AZs, no public IP assignment and attachment
   **Available**. Repeat in **Network / London** for `DCE-POC-SOURCE-VPC`
   (`10.10.0.0/16`, four subnets, attachment **Available**).
   Source application route tables must route `10.20.0.0/16` to TGW; target application
   tables must route `10.10.0.0/16` to TGW. Attachment-subnet tables keep local routes.
   TGW propagation alone does not install these VPC routes.
8. **Stage 3 — security.** Merge the security fragment, preserving all other `centralSecurityServices`
   children. Set exclusions to every enabled region except London. Stop and reassess if existing
   configuration conflicts with `deploymentTargets`. Deploy and verify: Audit account administrator
   role; GuardDuty and Security Hub CSPM enabled in London. Preserve generated Audit
   naming; stop if another delegated administrator or pre-existing enabled configuration
   conflicts. In **Audit / London**, open each service's Accounts view: verify the lab
   members are enabled/associated, and check Management separately. In each account,
   Security Hub CSPM → Security standards: verify **AWS Foundational Security Best
   Practices v1.0.0** is enabled and checks have results (pending is not completion).
   Failed controls may be expected with deliberately omitted services: record them, do
   not claim a compliant score. No findings means no detected findings, not proof of safety.
9. **Stage 4 — tags.** Follow sections 05E and 05F for the global tags fragment.
10. **Stage 5 — controls.** In CodeCommit → Code → **Add file → Create file**, paste the
    supplied JSON at `service-control-policies/dce-poc-deny-create-user.json` and commit.
    Merge fragments 06/07 into the existing organization/security files, preserving
    existing arrays and recorder settings. Do not change the SCP strategy or existing
    Control Tower policies. Review all three file changes, then release once and approve.
    The SCP targets only Non-Production, not Root, Management or the security accounts.
    Verify Organizations → Policies → SCPs → its Targets, and **NonProduction / London →
    Config → Rules** for the required-Project-tag rule. An absent/stopped EC2 recorder
    must be resolved through Control Tower; do not create a competing recorder.
11. Continue with [05b — Workload migration and testing](05b-workload-migration-and-testing.md).

**If you deployed the previous one-VPC draft:** do not paste a second TGW or duplicate
the target VPC. Keep their existing names; add only the source VPC entry and the two
target application routes from the new fragment. Review the diff for additions, not
replacements/deletions, then deploy. Existing subnet and attachment names stay unchanged.

## Review gates

- Review your proposed configuration **before releasing**. The pipeline's manual approval
  is after Prepare / Accounts / Bootstrap; new accounts can be created before approval.
- Compare the deployed **Configuration source commit** against the reviewed commit ID.
- No concurrent runs. One change, one review, one approval.
- After each stage, wait for full pipeline success and match its Configuration source
  commit to the latest reviewed `main` commit. Save screenshots with account/Region and
  resource IDs: five accounts, network share/attachment/routes, security members and tags.

## Cost note
Ongoing cost is driven by two TGW attachments, security services and the existing baseline.
05b adds two EC2 instances/EBS volumes and four interface-endpoint AZ units. The old
baseline estimate is invalid for this POC; re-estimate before approval.

## Cleanup

- Use the official LZA uninstall guide and the Control Tower decommission guide; see
  [05-lza-pipeline-implementation-runbook.md](05-lza-pipeline-implementation-runbook.md) for links.
- Preserve logs before teardown. Removing the YAML files does not guarantee resource deletion;
  account closure is a separate action from resource cleanup.
- Inventory the exact added resource IDs first. Attachment associations/propagations and
  attachments depend on the VPC/TGW: remove dependants before their parents under the
  official uninstall flow, checking retained resources. Verify security-service state
  and Bills afterward; do not assume disabling a YAML field removes all retained data.

## Local validation (no AWS)

```
python3 poc-config/validate_fragments.py /path/to/pinned/lza-checkout
```
The validator runs against a reviewed source checkout. It is not an AWS-tested validation, and full
merged-configuration validation remains outstanding.

Source: [LZA account, OU, network and security configuration guidance](https://docs.aws.amazon.com/solutions/latest/landing-zone-accelerator-on-aws/performing-administrator-tasks.html).
Schema checks use the official `release/v1.16.3` checkout, not an invented template.
