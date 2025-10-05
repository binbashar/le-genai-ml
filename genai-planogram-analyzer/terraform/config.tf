#=============================#
# AWS Provider Settings       #
#=============================#
provider "aws" {
  region  = "us-west-2"
#   profile = var.profile
}

#=============================#
# Backend Config (partial)    #
#=============================#
terraform {
  required_version = "~> 1.2"

  required_providers {
    aws = "~> 5.0"
  }

  # backend "s3" {
  #   bucket         = "prisma-dev-genai-bedrock-poc-tfstate"
  #   key            = "terraform.tfstate"
  #   region         = "us-west-2"
  #   encrypt        = true
  #   dynamodb_table = "prisma-dev-genai-bedrock-poc-tfstate"
  # }
}

#=============================#
# Data sources                #
#=============================#

# Get default VPC
data "aws_vpc" "default" {
  default = true
}

# Get all subnets from default VPC
data "aws_subnets" "all" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
}

# data "terraform_remote_state" "ssl_cert" {
#   backend = "s3"

#   config = {
#     region  = var.region
#     profile = var.profile
#     bucket  = var.bucket
#     key     = "${var.environment}/security-certs/terraform.tfstate"
#   }
# }

# data "terraform_remote_state" "shared-dns" {
#   backend = "s3"

#   config = {
#     region  = var.region
#     profile = "${var.project}-shared-devops"
#     bucket  = "${var.project}-shared-terraform-backend"
#     key     = "shared/dns/binbash.co/terraform.tfstate"
#   }
# }
