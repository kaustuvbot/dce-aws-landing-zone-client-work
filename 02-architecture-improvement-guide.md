# 02 — Architecture Improvement Guide

> On hold following the client's instruction to use the existing diagram. This is historical editing guidance, not a prerequisite for [05 — the LZA lab](05-lza-pipeline-implementation-runbook.md). No further diagram changes are required for the current demo.

## Source diagram

[00-dce-lza-architecture-all-layers-v0.5-poc.drawio](/home/kaustuv/Documents/ChatGPT/Deji Amazon/DCE AWS Landing Zone Client Work/Architecture and Evidence/00-dce-lza-architecture-all-layers-v0.5-poc.drawio)

## Review result

Most requested labels already exist in v0.5. Do not recreate them.

Already present:

- Account and OU model
- Control Tower, SCPs, Config, CloudTrail, GuardDuty, Security Hub
- Entra ID and IAM Identity Center
- Direct Connect, VPN, Transit Gateway, and workload VPCs
- LZA foundation pipeline
- Terraform workload pipeline
- Foundation/workload ownership boundary
- Confirmed/proposed/optional legend

## Only add these items

### 1. Add AFT to the management account

Place a new box beside **Landing Zone Accelerator (LZA)**:

`Account Factory for Terraform (AFT)`

Subtitle:

`Approved request → governed AWS account`

Use the existing **pink/red management/governance style**.

### 2. Add the AFT account flow

Draw a **pink/red dashed arrow** from AFT to:

- Non-production workload account(s)
- Production workload account(s)

Label it:

`Account provisioning + baseline customisation`

Do not add another pipeline box. The existing LZA and Terraform pipeline flows are sufficient.

### 3. Add the POC boundary

Use a **grey dashed boundary**, matching the existing proposed/optional style, around only the items demonstrated:

- LZA configuration and deployment pipeline
- AFT account-vending flow
- One governed workload account
- Sample workload VPC and TGW attachment
- Central logging and security evidence
- Terraform workload deployment

Label the boundary:

`POC scope — validates the platform pattern, not production migration at scale`

### 4. Check existing arrows only

Do not redraw the network or security flows. Confirm that these existing paths remain readable:

`Legacy data centres → Direct Connect → Transit Gateway → Workload VPCs`

`CloudTrail → S3 central audit logs`

`GuardDuty → Security Hub`

`GitHub → Terraform + controlled CI/CD → Workload deployment`

If a line is hard to read, adjust its position only; keep its current colour and meaning.

## Colour rule

Reuse the source diagram palette:

- **Pink/red** — organisation, accounts, governance, security, AFT
- **Purple** — networking and workload VPC flows
- **Blue** — Entra ID and identity federation
- **Grey dashed** — proposed, optional, or POC boundaries

Do not introduce orange or new colours.

## Final check

- AFT is visible and connected to both workload OUs.
- POC scope is visibly smaller than the target architecture.
- Existing labels appear only once.
- Existing arrows retain their original colours.
- The diagram does not claim that the full production platform is complete.
