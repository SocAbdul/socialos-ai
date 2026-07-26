module "media" {
  source = "../../modules/media"

  name_prefix          = "socialos-staging"
  bucket_name          = var.media_bucket_name
  cors_allowed_origins = var.media_cors_allowed_origins

  tags = {
    LaunchStage = "private-beta"
  }
}

module "budget" {
  source = "../../modules/budget"

  name_prefix       = "socialos-staging"
  monthly_limit_usd = var.monthly_budget_limit_usd
  alert_email       = var.budget_alert_email
}

module "ecr" {
  source = "../../modules/ecr"

  name_prefix      = "socialos-staging"
  repository_names = ["api", "web"]

  tags = {
    LaunchStage = "private-beta"
  }
}

module "github_oidc" {
  source = "../../modules/github_oidc"

  name_prefix                = "socialos-staging"
  github_repository          = var.github_repository
  allowed_refs               = ["refs/heads/main"]
  existing_oidc_provider_arn = var.existing_github_oidc_provider_arn
  ecr_repository_arns        = values(module.ecr.repository_arns)

  tags = {
    LaunchStage = "private-beta"
  }
}

module "media_signer_iam" {
  source = "../../modules/media_signer_iam"

  name_prefix      = "socialos-staging"
  media_bucket_arn = module.media.bucket_arn
  kms_key_arn      = module.media.kms_key_arn

  tags = {
    LaunchStage = "private-beta"
  }
}
