# 01 — Demo Mandatory Requirements

## Purpose

Prove that the proposed AWS platform can govern accounts, deploy safely, and support a migration workload.

## Demo pass checklist

| # | Capability | Minimum proof | Evidence |
|---|---|---|---|
| 1 | Multi-account foundation | OUs and governed accounts exist | Organizations screenshot |
| 2 | LZA foundation | Configuration is version-controlled and deployed by pipeline | Pipeline run |
| 3 | Account vending | A governed workload account can be requested/provisioned | AFT run or recorded walkthrough |
| 4 | Guardrails | SCP, Control Tower, or Config control blocks/detects an invalid change | Failed test or finding |
| 5 | Central logging | Account activity reaches the central log archive | CloudTrail/S3 evidence |
| 6 | Security posture | GuardDuty/Security Hub are enabled centrally | Findings/posture screenshot |
| 7 | Network pattern | Workload VPC attaches to Transit Gateway | TGW/VPC evidence |
| 8 | Workload delivery | Terraform deploys a small sample workload | Successful pipeline/deployment |
| 9 | Approval path | Change is reviewed before foundation/workload deployment | Pull request or approval evidence |
| 10 | Recovery/cleanup | Demo resources can be removed safely | Cleanup result |

## Required demo flow

1. Show the target architecture.
2. Commit or select a reviewed configuration change.
3. Run the foundation pipeline.
4. Show account vending or the approved AFT result.
5. Deploy the sample workload through Terraform.
6. Show logging, security, and network evidence.
7. Trigger one rejected or detected policy violation.
8. Explain what the POC proves and what remains for production.

## Mandatory evidence pack

- Architecture SVG
- Successful pipeline execution
- Account/OUs view
- AFT account request/result, or clearly labelled simulation
- TGW and workload VPC view
- Central CloudTrail/log archive evidence
- GuardDuty/Security Hub evidence
- Policy-control failure/detection evidence
- Workload deployment result
- Cleanup confirmation

## Not required for this POC

- Migrating 3,000 servers
- Production Direct Connect installation
- Full Entra ID integration
- Complete NCSC CAF/GDPR certification
- Full AFT self-service portal

These must be labelled as production follow-up work, not hidden as completed functionality.

## Definition of done

Every item in the pass checklist has either working AWS evidence or an explicit `POC simulation` label.
