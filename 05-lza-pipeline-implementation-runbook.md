# 05 — LZA Pipeline Implementation Runbook

## Goal

Deploy the official Landing Zone Accelerator (LZA) solution so AWS creates the pipeline used to manage the landing-zone foundation.

Expected pipeline name:

`AWSAccelerator-Pipeline`

## Important boundary

This runbook creates the foundation pipeline. It does not create the customer’s complete production platform or migrate servers.

## Phase 0 — Confirm the account is clean

Use the AWS Management Console in the new AWS account.

### Check these services

- **Organizations** — no existing OUs or member accounts
- **Control Tower** — no existing landing zone
- **IAM Identity Center** — not already configured
- **AWS Config** — no existing organisation-wide setup
- **CloudTrail** — no conflicting organisation trail

If any of these already exist, stop. Do not continue until the configuration is understood.

LZA can create or manage Control Tower, but existing organisation configuration can cause conflicts.

## Phase 1 — Secure and prepare the account

### 1. Secure root access

Console: **IAM → Dashboard**

- Enable MFA for the root user.
- Do not create root access keys.
- Keep root credentials out of repositories and screenshots.

### 2. Choose the home Region

Set the console Region to:

`Europe (London) — eu-west-2`

Use the same Region for the installer, Secrets Manager, and LZA resources.

The Control Tower home Region cannot be changed after landing-zone setup.

### 3. Create a budget

Console: **Billing and Cost Management → Budgets**

Create a monthly budget with alerts at 50%, 80%, and 100%.

Control Tower, CloudTrail, Config, S3, CloudWatch, CodeBuild, and networking resources may incur charges.

### 4. Create a working administrator

Use IAM Identity Center or a named IAM administrator for setup. Avoid using the root user for deployment.

Record the administrator name, account ID, Region, and budget alert email in private notes.

## Phase 2 — Prepare GitHub access

LZA needs access to its AWS configuration repository.

### 5. Create a GitHub token

Create a GitHub personal access token with the minimum permission required by the current LZA documentation.

For the public AWS LZA repository, the documented requirement is `public_repo` access.

Do not paste the token into the LZA YAML files, screenshots, or Git commits.

### 6. Store the token in Secrets Manager

Console: **Secrets Manager → Store a new secret**

- Secret type: **Other type of secret**
- Secret value: token as plain text
- Secret name: `accelerator/github-token`
- Region: `eu-west-2`
- Rotation: disabled for this POC

Verify the name character-for-character. Do not expose the secret value after saving.

## Phase 3 — Prepare AWS Organizations

### 7. Create or verify the organisation

Console: **AWS Organizations → Settings**

- Use **All features**.
- Confirm the account email is verified and controlled by you.
- Do not create OUs manually for this clean POC.
- Do not add member accounts manually.

The LZA installer needs to create the foundation structure cleanly.

### 8. Check CodeBuild quota

Console: **Service Quotas → AWS CodeBuild**

Check:

`Concurrently running builds for Linux/Large environment`

If the applied quota is below 3, request an increase before continuing.

## Phase 4 — Launch the official LZA installer

### 9. Open the official LZA implementation guide

Use the current AWS solution documentation and choose the official **AWSAccelerator-InstallerStack** CloudFormation template.

Do not download or modify the installer template.

### 10. Launch CloudFormation

Console: **CloudFormation → Create stack → With new resources**

- Use the official LZA installer template URL.
- Confirm the Region is `eu-west-2`.
- Choose **Next**.

### 11. Enter installer parameters

Use the current template’s parameter names. For this POC, select values equivalent to:

- Home Region: `eu-west-2`
- Control Tower integration: enabled
- Control Tower deployment: enabled for a clean organisation
- GitHub token secret: `accelerator/github-token`
- Deployment Regions: `eu-west-2` initially
- Repository and branch: use the template defaults unless the client has specified otherwise

Do not invent account IDs, OUs, Regions, or email addresses. Use the values displayed by the template.

### 12. Configure stack options

- Add tags such as `Project=DCE-POC` and `Owner=<your-name>`.
- Keep rollback enabled.
- Review IAM capability acknowledgements.
- Submit the stack.

Wait for `CREATE_COMPLETE`.

If the stack fails, open the **Events** tab, record the first meaningful failure, and stop. Do not repeatedly rerun the installer.

## Checkpoint A — Installer evidence

Capture:

- CloudFormation stack name
- Stack status `CREATE_COMPLETE`
- Region `eu-west-2`
- Relevant stack Outputs
- No secret values

## Phase 5 — Validate the generated LZA pipeline

### 13. Open CodePipeline

Console: **Developer Tools → CodePipeline**

Find:

`AWSAccelerator-Pipeline`

### 14. Compare the stages with the client reference

The exact stage names may vary by LZA version. Confirm that the pipeline contains equivalent foundation stages for:

- Source
- Prepare
- Accounts
- Bootstrap
- Logging
- Organization
- Security
- Network
- Operations

Do not rename generated stages just to match the screenshot.

### 15. Wait for the first execution

- Open the execution details.
- Wait for all applicable stages to finish.
- Open any failed action and record the error.
- Capture the successful execution view.

The first deployment may take a long time because it creates Control Tower, shared accounts, security controls, and foundation resources.

## Checkpoint B — Pipeline evidence

Capture:

- Pipeline name
- Source revision
- Stage list
- Successful execution
- One action detail showing the deployment completed

## Phase 6 — Validate the landing zone

### 16. Open Control Tower

Confirm:

- Landing zone is healthy.
- Security OU exists.
- Log Archive account exists.
- Audit account exists.
- Foundation/Sandbox or workload OU exists.

### 17. Open Organizations

Confirm that accounts and OUs match the architecture at a minimum:

- Management account
- Security OU
- Log Archive account
- Audit account
- Infrastructure/workload area as created by the selected configuration

### 18. Validate security and logging

Check:

- CloudTrail organisation trail
- Central log destination
- GuardDuty status
- Security Hub status
- Control Tower controls/compliance view

Capture evidence without exposing sensitive data.

## Phase 7 — Make one safe pipeline change

Only after the first run is healthy:

1. Open the generated LZA configuration repository.
2. Create a branch.
3. Make one harmless, documented configuration change.
4. Open a pull request or use the approved review method.
5. Run validation.
6. Approve and release the pipeline.
7. Capture the second successful execution.

Do not change SCPs, Regions, account emails, networking CIDRs, or security controls for the first test.

## Phase 8 — Account vending demonstration

For the first POC, use the available Control Tower Account Factory path to demonstrate governed account creation.

If AFT is not installed by the selected LZA template:

- Show the AFT position in the architecture.
- Explain that AFT is the next automation layer.
- Do not claim that AFT was deployed.

## Phase 9 — Evidence pack

Save these screenshots in a private evidence folder:

- CloudFormation installer success
- `AWSAccelerator-Pipeline` overview
- Successful first execution
- Successful configuration change execution
- Control Tower landing-zone health
- Organisations/OUs
- Security controls/compliance
- CloudTrail/log archive
- GuardDuty/Security Hub

Mask account IDs, email addresses, repository tokens, URLs containing sensitive query values, and personal information before using screenshots in the presentation.

## Cleanup and cost control

- Delete only test workload resources.
- Review NAT Gateway, VPC, EC2, CloudTrail, Config, S3, CodeBuild, and CloudWatch usage.
- Keep the landing zone if it will be used for the recorded demo.
- Do not reset or delete Control Tower without a separate recovery plan.

## Completion criteria

- Installer stack is healthy.
- `AWSAccelerator-Pipeline` exists.
- First pipeline execution is successful.
- One safe configuration change is demonstrated.
- Control Tower and shared accounts are visible.
- Security/logging evidence is captured.
- Customer-owned items are explained, not falsely presented as implemented.

## Official references

- [LZA prerequisites](https://docs.aws.amazon.com/solutions/latest/landing-zone-accelerator-on-aws/prerequisites.html)
- [LZA installer stack](https://docs.aws.amazon.com/solutions/latest/landing-zone-accelerator-on-aws/step-1.-launch-the-stack.html)
- [AWS Control Tower getting started](https://docs.aws.amazon.com/controltower/latest/userguide/getting-started-with-control-tower.html)
