#================================#
# Common variables               #
#================================#
#
# config/base.config
#
#=============================#
# Project Variables           #
#=============================#
variable "project" {
  type        = string
  description = "Project Name"
}

variable "project_long" {
  type        = string
  description = "Project Long Name"
}

variable "environment" {
  type        = string
  description = "Environment Name"
}

#================================#
# Local variables                #
#================================#
variable "oidc_provider" {
  type = object({
    url       = string
    audiences = list(string)
    owner     = string
    repos     = list(string)
  })
}
