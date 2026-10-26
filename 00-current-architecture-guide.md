# 00 — Current Architecture Guide

## Purpose

Use this guide to understand the existing diagram before editing it.

## Read the diagram in four layers

### 1. Organisation and governance

The outer AWS Organisation boundary contains the management account, OUs, and governed accounts.

- **Management account** — owns organisation-level administration and LZA.
- **Security OU** — central audit logs and security tooling.
- **Infrastructure OU** — network and shared platform services.
- **Non-Production OU** — development and test workloads.
- **Production OU** — production workloads with stronger controls.

Controls apply across OUs:

`SCPs + Control Tower controls + AWS Config rules`

### 2. Identity and security

The workforce identity flow is:

`Microsoft Entra ID → IAM Identity Center → permission sets`

Security evidence flows to central services:

`CloudTrail → S3 Log Archive`

Security services provide central detection and posture management:

`GuardDuty → Security Hub`

Break-glass access is shown as a separate emergency path and still requires customer agreement.

### 3. Hybrid network

The proposed data-centre connectivity flow is:

`Legacy data centres → Direct Connect → Transit Gateway → workload VPCs`

VPN is shown as an optional interim or resilience path.

The Network account owns the central Transit Gateway. Workload accounts attach their VPCs to it.

### 4. Delivery lifecycle

There are two separate delivery paths.

#### Foundation lifecycle

`LZA configuration → LZA pipeline → governed foundation`

This manages accounts, controls, network, and security foundations.

#### Workload lifecycle

`GitHub → Terraform + CI/CD → workload deployment`

This manages workload resources only. It must not redeploy or replace the LZA foundation.

## What the current diagram already communicates

- London (`eu-west-2`) is the proposed primary region.
- AWS accounts are separated by function and environment.
- Security and logging are centralised.
- Hybrid connectivity uses a central network hub.
- Foundation and workload ownership are intentionally separated.

## What is currently missing or unclear

- AFT/account vending is not clearly shown.
- The account-request flow is not shown.
- The POC boundary is not visible.
- Some services are marked as proposed or still to be defined.
- Direct Connect, DNS, Entra ID, and break-glass decisions need confirmation.

## Simple explanation for the presentation

> The Landing Zone creates a governed AWS foundation. Central security and networking services protect and connect the accounts. LZA manages the foundation, while migration teams use controlled Terraform pipelines to deploy workloads into approved accounts.

## Diagram editing rule

Do not change the core account or network model unless new customer information requires it. Improve clarity by adding the missing AFT flow, ownership labels, colours, and POC boundary.

## Existing colour key

Reuse the source diagram’s current palette:

- **Pink/red** — organisation, accounts, OUs, governance, and security.
- **Purple** — Direct Connect, VPN, Transit Gateway, and workload VPC networking.
- **Blue** — Microsoft Entra ID and identity federation.
- **Grey dashed** — proposed, optional, or to-be-confirmed scope.

Use pink/red for the new AFT box and account-vending flow because AFT belongs to the management/governance layer. Do not introduce orange unless a genuinely new category needs its own visual language.
