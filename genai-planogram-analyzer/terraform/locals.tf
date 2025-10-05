locals {

  name = "${var.project}-${var.environment}"
  tags = {
    Terraform   = "true"
    Environment = var.environment
  }

  container_definitions = {
    prisma = {
      image                     = "574093079661.dkr.ecr.us-west-2.amazonaws.com/prisma-planogram-analyzer-prisma:latest"
      enable_cloudwatch_logging = false
      readonly_root_filesystem  = false
      cpu                       = 512
      memory                    = 1024
      port_mappings = [
        {
          "containerPort" : 8501,
          "hostPort" : 8501,
          "protocol" : "tcp"
        }
      ]
      environment = [
        {
          "name" : "AWS_DEFAULT_REGION"
          "value" : "us-west-2"
        },
        {
          "name" : "APP_USER"
          "value" : "prisma"
        }
      ]
      secrets = [
        {
          "name" : "APP_PASSWORD"
          "valueFrom" : "${module.secrets.secret_arns["/prisma-planogram-analyzer"]}:PWD_prisma::"
        }
      ]
    }
  }

  allowed_cidr = [
    {
      cidr        = "0.0.0.0/0",
      description = "Allow public access"
    }
  ]

  iam_role_statements = {
    bedrock = {
      actions = [
        "bedrock:InvokeModelWithResponseStream",
      "bedrock:InvokeModel"]
      effect    = "Allow"
      resources = ["*"]
    }
  }
}