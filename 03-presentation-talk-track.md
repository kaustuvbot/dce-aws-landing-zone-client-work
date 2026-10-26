# 03 — Presentation Talk Track

## Purpose

Use the existing architecture as the main visual. Explain the customer-owned areas verbally instead of adding more diagram detail.

## Opening message

> The design establishes a governed AWS foundation for a large-scale data-centre exit. It separates central platform controls from workload delivery so migration teams can work safely and repeatedly.

## Walk through the diagram

### 1. Organisation and accounts

> AWS Organizations and Control Tower provide the account structure and baseline governance. Security, infrastructure, non-production, and production responsibilities are separated into OUs and accounts.

### 2. Security and logging

> CloudTrail and central logging provide audit evidence. GuardDuty and Security Hub provide centralised threat detection and security posture visibility. SCPs, Control Tower controls, and Config rules provide preventative and detective controls.

### 3. Identity — customer-owned

> Workforce identity is expected to come from Microsoft Entra ID through IAM Identity Center using SAML federation and SCIM. The customer owns the directory, user lifecycle, groups, and access approvals. The platform team integrates with the approved customer pattern.

### 4. Network and hybrid connectivity

> The proposed migration path is from the legacy data centres through Direct Connect and Transit Gateway to workload VPCs. VPN remains an interim or resilience option, subject to network discovery and customer approval.

### 5. Foundation pipeline

> LZA configuration is version-controlled and deployed through the foundation pipeline. This pipeline manages the AWS foundation: accounts, controls, network, and security.

### 6. Workload delivery — customer-owned

> Migration teams own their GitLab or GitHub repositories and Terraform code. Their controlled CI/CD pipeline deploys workload resources into governed accounts. It does not manage or replace the LZA foundation.

## Key message to repeat

> The platform team governs the foundation; customer and migration teams consume it to deploy workloads.

## Keep these items verbal

- Entra ID integration details
- GitLab/GitHub ownership and repository model
- Terraform module standards
- Direct Connect implementation details
- DNS design
- Break-glass operating procedure
- Production compliance evidence

These are important design topics, but they do not need additional architecture boxes for this presentation.

## Closing message

> The POC demonstrates the repeatable platform pattern. Production implementation will confirm the customer-owned identity, network, repository, operational, and compliance details through discovery.
