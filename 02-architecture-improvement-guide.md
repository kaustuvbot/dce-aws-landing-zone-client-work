# 02 — Architecture Improvement Guide

## Source diagram

[00-dce-lza-architecture-all-layers.drawio.svg](/home/kaustuv/Documents/ChatGPT/Deji Amazon/DCE AWS Landing Zone Client Work/Architecture and Evidence/00-dce-lza-architecture-all-layers.drawio.svg)

## Goal

Make the architecture directly match the POC and demo checklist. Keep the current layout; add only missing flows and labels.

## Colour coding

Use the existing AWS-style colours where possible:

| Colour | Use for |
|---|---|
| Pink/red | Organisation, accounts, OUs, governance, security |
| Purple/blue | Network, Direct Connect, VPN, Transit Gateway, VPCs |
| Teal/green | Identity, logging, monitoring, evidence |
| Orange | CI/CD, LZA, AFT, Terraform, deployment flows |
| Grey dashed | Boundary, optional item, or to-be-confirmed design |

Line conventions:

- Solid arrow: confirmed or demonstrated flow
- Dashed arrow: proposed, optional, or pending approval
- Thick boundary: AWS organisation or POC scope
- Thin boundary: account, OU, or service grouping

Use the same colour for a component and its related arrows. Keep labels dark and readable.

## Step 1 — Add account vending

Place a new box in the **Management account**, beside **Landing Zone Accelerator (LZA)**:

`Account Factory for Terraform (AFT)`

Under it add:

`Approved account request → governed workload account`

Add a dashed arrow from AFT to:

- Non-production workload account(s)
- Production workload account(s)

Label the arrow:

`Account provisioning + baseline customisation`

## Step 2 — Clarify the foundation pipeline

Keep the existing bottom flow:

`LZA configuration files → LZA deployment pipeline → Governed foundation`

Change the pipeline label to:

`CI/CD: validate → approve → deploy`

Add a small note:

`Foundation: LZA / AWS-native`

## Step 3 — Clarify workload delivery

Keep the existing workload flow:

`GitHub → Terraform + controlled CI/CD → Workload deployment`

Add this note below it:

`Workload IaC only — does not deploy LZA`

This prevents confusion between platform ownership and migration-team ownership.

## Step 4 — Improve the network flow

Check that the diagram shows this direction clearly:

`Legacy data centres → Direct Connect → Transit Gateway → Workload VPCs`

Keep VPN as a secondary dashed path and label it:

`Interim / resilience option — confirm during network discovery`

Add a small box inside **Shared Services account**:

`Central DNS / resolver services`

Only keep this if DNS is part of the proposed POC; otherwise label it `To be confirmed`.

## Step 5 — Make security ownership clear

Inside the **Security OU**, label the Audit account:

`Delegated security administration`

Keep these services visible:

- CloudTrail
- Central S3 log archive
- GuardDuty
- Security Hub
- AWS Config

Add a short control label across the organisation boundary:

`Preventive: SCPs / Control Tower controls`

`Detective: Config / GuardDuty / Security Hub`

## Step 6 — Add identity and emergency access notes

Keep the Entra ID → IAM Identity Center flow.

Add below the break-glass box:

`Separate emergency access — approval and procedure required`

Do not claim that the break-glass design is final.

## Step 7 — Update the legend

Use three categories:

- Confirmed customer requirement
- Proposed POC design
- To be confirmed during discovery

Mark Direct Connect, DNS, break-glass access, and Entra ID integration according to their actual status.

## Step 8 — Add POC boundary

Add a dashed boundary around the components demonstrated in the POC:

- One governed workload account
- Sample VPC
- Transit Gateway attachment
- LZA pipeline
- AFT account-vending flow
- Central logging/security evidence
- Terraform workload deployment

Label it:

`POC scope — validates the platform pattern, not production migration at scale`

## Final review

- AFT is visible.
- Pipeline ownership is unambiguous.
- Network arrows are readable.
- Security services have a central owner.
- POC scope is visibly smaller than the target state.
- No component is presented as production-ready without evidence.
