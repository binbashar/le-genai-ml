module "alb" {
  source = "github.com/binbashar/terraform-aws-alb.git?ref=v9.9.0"

  name = "${var.project}-${var.environment}"

  internal = false

  load_balancer_type = "application"

  vpc_id                = data.aws_vpc.default.id
  subnets               = data.aws_subnets.all.ids
  create_security_group = true

  # # Security Group
  security_group_ingress_rules = merge(
    {
      for cidr_obj in local.allowed_cidr :
      "${replace(replace(cidr_obj.cidr, "/", "_"), ".", "_")}_80" => {
        from_port   = 80
        to_port     = 80
        ip_protocol = "tcp"
        description = cidr_obj.description
        cidr_ipv4   = cidr_obj.cidr
      }
    }
  )

  security_group_egress_rules = {
    all = {
      ip_protocol = "-1"
      cidr_ipv4   = "0.0.0.0/0"
    }
  }

  listeners = {
    http = {
      port     = 80
      protocol = "HTTP"
      
      # Default service is backend_node
      forward = {
        target_group_key = "default"
      }

      rules = []
    }
  }

  target_groups = {
    default = {
      backend_protocol                  = "HTTP"
      backend_port                      = 8080
      target_type                       = "ip"
      deregistration_delay              = 1
      load_balancing_cross_zone_enabled = true
      create_attachment                 = false

      health_check = {
        enabled             = true
        healthy_threshold   = 3
        interval            = 10
        matcher             = "200"
        path                = "/"
        port                = "traffic-port"
        protocol            = "HTTP"
        timeout             = 5
        unhealthy_threshold = 2

      }
    }
  }

  tags = local.tags
}
