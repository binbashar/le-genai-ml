#================================#
# S3 Terraform State Backend     #
#================================#
#
# This module creates an S3 bucket for storing Terraform state
#
# Reference: https://github.com/binbashar/terraform-aws-tfstate-backend/tree/v1.0.28
#

module "terraform_state_backend" {
  source = "git::https://github.com/binbashar/terraform-aws-tfstate-backend.git?ref=v1.0.28"

  # Naming
  namespace  = "client"
  stage      = "planogram-compliance-analyzer"
  name       = "tfstate"
  attributes = []

  # S3 Configuration
  bucket_replication_enabled = false
  force_destroy              = false

  # Security and Compliance Features
  block_public_acls       = true
  ignore_public_acls      = true
  block_public_policy     = true
  restrict_public_buckets = true

  # Encryption - Use default S3 encryption (AES-256)
  create_kms_key = false

  # Lifecycle
  bucket_lifecycle_enabled = true

  # Notifications (optional)
  notifications_sns = false
  notifications_sqs = false

  # VPC Configuration (optional)
  enforce_vpc_requests = false
  vpc_ids_list         = []

  # Tags
  tags = merge(local.tags, {
    Name        = "${local.name}-tfstate"
    Purpose     = "Terraform State Storage"
    ManagedBy   = "Terraform"
    Environment = var.environment
  })

  # Providers
  providers = {
    aws.primary   = aws
    aws.secondary = aws
  }
}

