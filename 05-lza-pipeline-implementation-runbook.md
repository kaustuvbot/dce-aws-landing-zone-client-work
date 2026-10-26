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

### 4. Create a temporary working administrator

For this clean LZA lab, do **not** configure IAM Identity Center yet. The LZA prerequisites may require it to be unused before Control Tower/LZA setup.

Create a temporary named IAM user for the installer, then delete or disable it after the landing zone is healthy.

#### Create the user

1. Open the AWS Console.
2. Search for **IAM**.
3. Open **IAM**.
4. In the left menu, choose **Users**.
5. Choose **Create user**.
6. User name: `dce-poc-bootstrap-admin`.
7. Select **Provide user access to the AWS Management Console**.
8. Choose **I want to create an IAM user**.
9. Set a strong console password.
10. Leave **Users must create a new password at next sign-in** selected if this is a personal lab.
11. Choose **Next**.

#### Grant temporary permissions

1. Choose **Attach policies directly**.
2. Search for `AdministratorAccess`.
3. Select **AdministratorAccess**.
4. Choose **Next**.
5. Review the user summary.
6. Choose **Create user**.
7. Copy the sign-in URL and user name to private notes.
8. Do not put the password in the repository or screenshots.

#### Enable MFA for the user

1. Open the new user.
2. Open the **Security credentials** tab.
3. In **Multi-factor authentication**, choose **Assign MFA device**.
4. Device name: `dce-poc-bootstrap-mfa`.
5. Choose **Authenticator app**.
6. Scan the QR code with an authenticator app.
7. Enter two consecutive MFA codes.
8. Choose **Add MFA**.

#### Sign in as the working administrator

1. Open a private/incognito browser window.
2. Open the copied IAM sign-in URL.
3. Sign in as `dce-poc-bootstrap-admin`.
4. Complete the MFA prompt.
5. Confirm the account ID and Region in the console header.
6. Continue the runbook using this user, not the root user.

#### Important cleanup

After the LZA pipeline and landing zone are healthy:

1. Sign in through the approved IAM Identity Center path once it has been configured.
2. Open **IAM → Users → dce-poc-bootstrap-admin**.
3. Choose **Delete user** only after confirming you have another working administrator.

This temporary user is a lab bootstrap mechanism, not the target production access model.

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

### 14. Identify the configuration source

Open the pipeline and inspect the **Source** action.

- If it shows **CodeCommit**, open the linked repository from the action.
- If it shows **GitHub**, open the linked repository and branch.
- Use the repository and branch created by your installer; do not assume it matches the client’s repository name.

The client evidence shows a CodeCommit repository named `aws-accelerator-config`. Your new lab may use a different repository depending on the LZA template version and source settings.

### 15. Compare the stages with the client reference

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

### 16. Wait for the first execution

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

## Phase 6 — Edit the LZA configuration repository

This is the main hands-on part of the lab. Edit the configuration repository; do not edit generated pipeline code.

### 17. Find the configuration files

The repository normally contains files similar to:

```text
accounts-config.yaml
global-config.yaml
iam-config.yaml
network-config.yaml
organization-config.yaml
security-config.yaml
```

The exact names may vary by LZA version. Use the files present in your generated repository as the source of truth.

### 18. Understand file ownership

| File | Purpose | First-lab action |
|---|---|---|
| `organization-config.yaml` | OUs and organisation settings | Read only |
| `accounts-config.yaml` | Account definitions and placement | Read only |
| `global-config.yaml` | Regions, tags, and global settings | Use for one safe change |
| `iam-config.yaml` | Roles and permission sets | Read only |
| `network-config.yaml` | VPCs, TGW, and network settings | Read only |
| `security-config.yaml` | Guardrails and security services | Read only |

Do not copy the client’s account IDs, email addresses, CIDRs, or environment names into your lab.

### 19. Make one safe configuration change

Use the syntax already supplied in your generated repository.

Preferred first change:

- Add or update a non-sensitive project tag only if the existing file already contains a valid tag block.
- Keep the existing YAML structure and indentation.
- Change one value only.
- Do not change account IDs, Regions, OUs, SCPs, CIDRs, IAM permissions, or security controls.

If no safe tag or metadata field exists, do not invent one. Use the initial successful run as the configuration demonstration and record `No safe configuration change made`.

### 20. Commit the change

For **CodeCommit**:

1. Open **Developer Tools → CodeCommit → Repositories**.
2. Open the repository linked in the pipeline Source action.
3. Select the target branch.
4. Open the configuration file and choose **Edit**.
5. Make the single safe change.
6. Commit with a message such as `POC: add DCE demo project tag`.

For **GitHub**, edit the linked repository and branch shown in the Source action, then create a branch or pull request.

### 21. Release and validate the pipeline

1. Open **CodePipeline → `AWSAccelerator-Pipeline`**.
2. Confirm a new execution appears.
3. If automatic triggering is disabled, choose **Release change**.
4. Wait for every applicable stage to complete.
5. Capture the source revision, stage results, and final status.

The proof is:

`Repository change → pipeline execution → governed foundation result`

If the pipeline fails, capture the first failed action, revert the last change, and rerun only after the configuration is valid. Do not edit generated CloudFormation, CodeBuild, or Control Tower resources to force a green pipeline.

## Phase 7 — Validate the landing zone

### 22. Open Control Tower

Confirm:

- Landing zone is healthy.
- Security OU exists.
- Log Archive account exists.
- Audit account exists.
- Foundation/Sandbox or workload OU exists.

### 23. Open Organizations

Confirm that accounts and OUs match the architecture at a minimum:

- Management account
- Security OU
- Log Archive account
- Audit account
- Infrastructure/workload area as created by the selected configuration

### 24. Validate security and logging

Check:

- CloudTrail organisation trail
- Central log destination
- GuardDuty status
- Security Hub status
- Control Tower controls/compliance view

Capture evidence without exposing sensitive data.

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
