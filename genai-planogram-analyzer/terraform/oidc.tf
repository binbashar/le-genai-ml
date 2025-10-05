// Get the GitHub OIDC provider certificate
data "tls_certificate" "github" {
  url = "https://token.actions.githubusercontent.com/.well-known/openid-configuration"
}

# Add identity provider for OIDC
resource "aws_iam_openid_connect_provider" "github" {
  url             = var.oidc_provider.url
  client_id_list  = var.oidc_provider.audiences
  thumbprint_list = [data.tls_certificate.github.certificates[0].sha1_fingerprint]
}

module "oidc_role" {
  source = "github.com/binbashar/terraform-aws-iam.git//modules/iam-assumable-role-with-oidc?ref=v5.52.2"

  create_role = true
  role_name   = "github-oidc-role"

  provider_url                   = aws_iam_openid_connect_provider.github.url
  oidc_fully_qualified_audiences = aws_iam_openid_connect_provider.github.client_id_list

  oidc_subjects_with_wildcards = [
    for repo in var.oidc_provider.repos : "repo:${var.oidc_provider.owner}/${repo}:*"
  ]

  inline_policy_statements = [
    {
      sid     = "AllowAssumeRole"
      effect  = "Allow"
      actions = ["sts:*"]
      resources = [
        "arn:aws:iam::*:role/github-oidc-role-*"
      ]
    }
  ]

  role_policy_arns = [
    aws_iam_policy.ecr_sts_policy.arn
  ]
}

// ECR and STS policies to allow OIDC role to access ECR and STS
data "aws_iam_policy_document" "ecr_sts_policy" {
  statement {
    sid    = "AllowECRAccess"
    effect = "Allow"
    actions = [
      "ecr:GetDownloadUrlForLayer",
      "ecr:DescribeImages",
      "ecr:DescribeRepositories",
      "ecr:ListImages",
      "ecr:PutImage",
      "ecr:InitiateLayerUpload",
      "ecr:UploadLayerPart",
      "ecr:CompleteLayerUpload"
    ]
    resources = ["arn:aws:ecr:us-west-2:574093079661:repository/*"]
  }
  statement {
    sid    = "AllowGetAuthorizationToken"
    effect = "Allow"
    actions = [
      "ecr:GetAuthorizationToken",
      "ecr:BatchCheckLayerAvailability",
      "ecr:GetDownloadUrlForLayer",
      "ecr:BatchGetImage"
    ]
    resources = ["*"]
  }
  statement {
    sid    = "AllowAssumeRole"
    effect = "Allow"
    actions = [
      "sts:AssumeRole",
      "sts:TagSession"
    ]
    resources = ["*"]
  }
  statement {
    sid    = "AllowECSUpdate"
    effect = "Allow"
    actions = [
      "ecs:UpdateService",
      "ecs:DescribeServices",
      "ecs:DescribeClusters",
      "ecs:ListServices",
      "ecs:DescribeTaskDefinition",
      "ecs:RegisterTaskDefinition",
      "ecs:ListTaskDefinitions"
    ]
    resources = ["*"]
  }
}

resource "aws_iam_policy" "ecr_sts_policy" {
  name        = "github-ecr-ecs-sts-policy"
  description = "Policy to allow OIDC role to access ECR, ECS, and STS"
  policy      = data.aws_iam_policy_document.ecr_sts_policy.json
}