project_long = "client"
project = "client"
environment = "planogram-analyzer"

oidc_provider = {
  url       = "https://token.actions.githubusercontent.com"
  audiences = ["sts.amazonaws.com"]
  owner     = "karacas"
  repos     = ["clientVisionBinBash"]
}