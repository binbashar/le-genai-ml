# AWS Profile Migration Notes

This document summarizes the changes made to remove hardcoded `AWS_PROFILE=binbash` references and make the workshop materials suitable for multiple participants, each using their own AWS profile.

## Summary of Changes

### Documentation Updates

#### 1. Main README (`README.md`)
- ✅ Updated AWS Configuration section with comprehensive AWS SSO and IAM user setup instructions
- ✅ Added step-by-step profile configuration guide
- ✅ Added reference link to new `AWS_SETUP.md` guide
- ✅ Updated CDK bootstrap section to use generic profile name
- ✅ Added note about replacing `binbash` references with user's own profile

#### 2. Pre-Workshop Checklist (`PRE_WORKSHOP_CHECKLIST.md`)
- ✅ Completely rewrote AWS Account Setup section (Section 1)
- ✅ Added both AWS SSO and IAM user credential options
- ✅ Updated all command examples to use `your-profile-name` placeholder
- ✅ Added verification steps and troubleshooting tips
- ✅ Updated CDK bootstrap commands
- ✅ Updated environment variables section
- ✅ Fixed all troubleshooting commands to use generic profiles
- ✅ Added reference link to `AWS_SETUP.md`

#### 3. Instructor Guide (`INSTRUCTOR_GUIDE.md`)
- ✅ Updated Quick Fixes table to show generic profile commands
- ✅ Changed `aws sso login --profile binbash` to `aws sso login --profile your-profile-name`
- ✅ Updated backup plan requirements section

#### 4. Finance Personal Assistant README (`finance-personal-assistant/README.md`)
- ✅ Added new "AWS Profile Configuration" section
- ✅ Provided both SSO and IAM setup options
- ✅ Added verification commands
- ✅ Noted that users should replace `binbash` with their own profile

#### 5. Workshop README (`finance-personal-assistant/workshop/README.md`)
- ✅ Updated Prerequisites Check section
- ✅ Added AWS profile configuration instructions
- ✅ Added important note about replacing `binbash` references

### New Documentation

#### 6. AWS Setup Guide (`AWS_SETUP.md`) - **NEW FILE**
Comprehensive 400+ line guide covering:
- ✅ AWS SSO setup (step-by-step with all prompts)
- ✅ IAM user credential configuration
- ✅ Verification procedures
- ✅ CDK bootstrap instructions
- ✅ Extensive troubleshooting section
- ✅ Quick reference commands
- ✅ Security best practices
- ✅ Session management for SSO

### Script Updates

#### 7. Demo Launch Script (`demo.sh`)
- ✅ Removed hardcoded `export AWS_PROFILE=binbash`
- ✅ Added profile validation check
- ✅ Shows helpful error message if `AWS_PROFILE` not set
- ✅ Displays active profile when launching
- ✅ References `AWS_SETUP.md` in error message

#### 8. UI Demo Script (`ui/demo.sh`)
- ✅ Updated comment to use generic profile name
- ✅ Changed from `AWS_PROFILE=binbash` to `export AWS_PROFILE=your-profile-name` in documentation

## What Workshop Participants Need to Do

### Before the Workshop

1. **Configure AWS Profile:**
   ```bash
   # Option 1: AWS SSO (recommended)
   aws configure sso

   # Option 2: IAM user credentials
   aws configure --profile workshop
   ```

2. **Set Environment Variable:**
   ```bash
   # Add to ~/.bashrc or ~/.zshrc for persistence
   export AWS_PROFILE=workshop  # or your chosen profile name
   ```

3. **Verify Configuration:**
   ```bash
   aws sts get-caller-identity
   ```

4. **Bootstrap CDK (one-time):**
   ```bash
   ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
   cdk bootstrap aws://$ACCOUNT_ID/us-west-2
   ```

### During the Workshop

- Ensure `AWS_PROFILE` environment variable is set in your terminal
- All scripts now respect this environment variable
- No need to edit scripts or configuration files

### If You See `binbash` References

If you encounter any remaining references to `binbash`:
- **In documentation:** Replace with your own profile name
- **In scripts:** Export your `AWS_PROFILE` before running
- **In error messages:** Contact the instructor

## Remaining Hardcoded References

The following scripts still contain hardcoded references but are **production scripts** (not workshop materials):

### Production Scripts (Not Workshop Materials)

These scripts are in `finance-personal-assistant/production/` and are used for development, not during the workshop:

1. **`finance-personal-assistant/production/cdk/deploy.sh`**
   - Used by developers for CDK infrastructure deployment
   - Workshop participants typically don't use this directly

2. **`finance-personal-assistant/production/launch.sh`**
   - Wraps `agentcore launch` command
   - Respects exported `AWS_PROFILE` environment variable

3. **`finance-personal-assistant/production/configure.sh`**
   - Wraps `agentcore configure` command
   - Respects exported `AWS_PROFILE` environment variable

4. **`finance-personal-assistant/production/health.sh`**
   - Health check script
   - Takes `--profile` argument or respects `AWS_PROFILE` env var

5. **`scripts/reset_memory.sh`**
   - Utility script for clearing agent memory
   - Not used in standard workshop flow

### Why These Scripts Still Reference `binbash`

These scripts are used for **production development** and may contain hardcoded profile references for the original developer's environment. However:
- They all respect the `AWS_PROFILE` environment variable
- Workshop participants should export their own profile before running any script
- The workshop primarily uses Jupyter notebooks, not these scripts

### Recommended Approach for Production Scripts

If you need to run production scripts:

```bash
# Set your profile globally for the session
export AWS_PROFILE=your-profile-name

# All scripts will now use your profile
./launch.sh
./health.sh
./configure.sh
```

## Testing Your Configuration

Run this checklist to verify everything is configured correctly:

```bash
# 1. Check AWS CLI is installed
aws --version
# Expected: aws-cli/2.x.x

# 2. Verify profile is set
echo $AWS_PROFILE
# Expected: your-profile-name

# 3. Test credentials
aws sts get-caller-identity
# Expected: Your account ID and ARN

# 4. Check region
aws configure get region
# Expected: us-west-2 (or your configured region)

# 5. Test demo.sh script
./demo.sh
# Expected: No error about missing AWS_PROFILE
```

All checks passed? ✅ You're ready for the workshop!

## Resources

- **Comprehensive Setup Guide:** [AWS_SETUP.md](./AWS_SETUP.md)
- **Quick Start:** [README.md](./README.md)
- **Workshop Materials:** [finance-personal-assistant/workshop/README.md](./finance-personal-assistant/workshop/README.md)
- **Pre-Workshop Checklist:** [PRE_WORKSHOP_CHECKLIST.md](./PRE_WORKSHOP_CHECKLIST.md)

## Questions or Issues?

- **During workshop:** Ask your instructor
- **Before workshop:** Review [AWS_SETUP.md](./AWS_SETUP.md) troubleshooting section
- **Technical issues:** Check [TROUBLESHOOTING.md](./TROUBLESHOOTING.md) (if available)

---

**Last Updated:** 2025-01-06
**Change Summary:** Removed all hardcoded `AWS_PROFILE=binbash` references from documentation and workshop scripts to support multiple workshop participants with their own AWS profiles.
