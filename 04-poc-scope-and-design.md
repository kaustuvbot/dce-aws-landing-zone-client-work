# 04 — POC Scope and Design

## Purpose

Prove the core platform pattern with the smallest safe demonstration.

## POC includes

- Existing LZA foundation configuration
- Management account and core OU structure
- One governed workload account
- One sample workload VPC
- Transit Gateway attachment
- Central CloudTrail/log archive evidence
- GuardDuty and Security Hub evidence
- Foundation pipeline execution
- Small Terraform workload deployment
- One account-vending explanation or AFT walkthrough

## POC follows the diagram

| Diagram area | POC proof |
|---|---|
| Organisation/OUs | Account is governed and placed correctly |
| Security OU | Logs and security posture are centralised |
| Infrastructure OU | TGW and workload attachment are visible |
| LZA pipeline | Foundation change is reviewed and deployed |
| Workload pipeline | Sample workload is deployed into the governed account |
| Customer-owned areas | Explained verbally, not reimplemented |

## Customer-owned: talk through only

- Microsoft Entra ID integration
- GitLab/GitHub repository ownership
- Terraform module standards
- Direct Connect production circuit
- DNS and resolver decisions
- Break-glass access procedure

## Demo success criteria

The audience can see that:

1. Accounts can be governed consistently.
2. Foundation changes are controlled through CI/CD.
3. Workloads can be deployed into approved accounts.
4. Logging and security evidence is centralised.
5. The pattern can be repeated for migration waves.

## Excluded from the POC

- 3,000-server migration
- Production Direct Connect installation
- Full Entra ID integration
- Full AFT service rollout for 12 teams
- Complete NCSC CAF or GDPR assessment
- Production operational handover

## POC positioning

> This is a technical pattern demonstration, not a production certification or complete migration implementation.
