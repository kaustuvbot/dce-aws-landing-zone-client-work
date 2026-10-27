# 04 — POC Scope and Design

## Purpose

Prove the core platform pattern with the smallest safe demonstration.

## POC includes

- Fresh AWS lab using the official LZA installer and its generated configuration
- Management, Audit and LogArchive accounts with the generated landing-zone structure
- Network and NonProduction accounts in Infrastructure and Non-Production OUs
- London Transit Gateway in Network, shared with NonProduction through AWS RAM
- Two private two-AZ VPCs (temporary source and workload target), two TGW attachments and bidirectional routes
- Two small EC2 instances, private Systems Manager access and a synthetic application/database migration
- One preventive SCP test and one detective AWS Config tag-rule test
- GuardDuty and Security Hub in London with Audit as delegated administrator
- Installer pipeline and foundation pipeline execution
- CodeCommit YAML change, manual review and verification on a deployed resource
- Central CloudTrail/log-delivery evidence
- Observed control and security-service status, with undeployed capabilities labelled clearly

Follow [05 — LZA pipeline lab](05-lza-pipeline-implementation-runbook.md), including
[05a — POC configuration and network demo](05a-poc-configuration-and-network-demo.md)
at Phase E, then [05b — migration and tests](05b-workload-migration-and-testing.md).
Architecture editing is paused; the diagram remains the wider target design.
This expands the previous tags-only demonstration. Configuration is not deployed proof:
mark each capability complete only after its verification checkpoint passes.

## POC follows the diagram

| Diagram area | POC proof |
|---|---|
| Organisation/OUs | Generated shared accounts and governance are visible |
| Security OU | Central log delivery; London GuardDuty/Security Hub administrator and member status |
| Infrastructure OU | Network account owns the TGW and its RAM share |
| Non-Production OU | One workload VPC with private subnets and a TGW attachment |
| LZA pipeline | Configuration change reaches deployed resources through the pipeline |
| Workload pipeline | Explain customer-owned Terraform/GitLab delivery |
| Customer-owned areas | Explained verbally, not reimplemented |

## Customer-owned: talk through only

- Microsoft Entra ID integration
- GitLab/GitHub repository ownership
- Terraform module standards
- Terraform workload deployment
- AFT account vending and the 12-team rollout
- Shared Services account and production workload accounts
- Direct Connect production circuit
- DNS and resolver decisions
- Break-glass access procedure

## Demo success criteria

The audience can see that:

1. Accounts can be governed consistently.
2. Foundation changes are controlled through CI/CD.
3. A YAML change produces a verifiable AWS resource change.
4. Central log delivery has evidence; enabled and proposed security capabilities are distinguished.
5. The operating pattern is explained without claiming migration-scale performance was tested.
6. The workload VPC attachment, TGW association and propagated VPC CIDR are visible.

The two-VPC test demonstrates private application traffic over TGW, transfer integrity,
application restart/persistence, route dependency and two governance controls. It does not
prove real on-premises reachability or server replication. No NAT gateway, internet
gateway or Route 53 Resolver endpoint is added. Four SSM interface endpoints provide
private administration. The diagram's five-year retention remains a target; the lab
preserves its generated retention settings.

## Excluded from the POC

- 3,000-server migration
- Production Direct Connect installation
- Full Entra ID integration
- Full AFT service rollout for 12 teams
- Complete NCSC CAF or GDPR assessment
- Production operational handover

## POC positioning

> This is a technical pattern demonstration, not a production certification or complete migration implementation.
