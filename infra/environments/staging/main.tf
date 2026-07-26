module "media" {
  source = "../../modules/media"

  name_prefix          = "socialos-staging"
  bucket_name          = var.media_bucket_name
  cors_allowed_origins = var.media_cors_allowed_origins

  tags = {
    LaunchStage = "private-beta"
  }
}

module "network" {
  source = "../../modules/network"

  name_prefix          = "socialos-staging"
  vpc_cidr             = var.vpc_cidr
  public_subnet_cidrs  = var.public_subnet_cidrs
  private_subnet_cidrs = var.private_subnet_cidrs

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

module "postgres" {
  count = var.enable_staging_runtime ? 1 : 0

  source = "../../modules/postgres"

  name_prefix           = "socialos-staging"
  vpc_id                = module.network.vpc_id
  subnet_ids            = module.network.private_subnet_ids
  allowed_cidr_blocks   = [module.network.vpc_cidr_block]
  instance_class        = var.staging_postgres_instance_class
  allocated_storage_gb  = var.staging_postgres_allocated_storage_gb
  backup_retention_days = var.staging_postgres_backup_retention_days
  deletion_protection   = false
  skip_final_snapshot   = true

  tags = {
    LaunchStage = "private-beta"
  }
}

module "redis" {
  count = var.enable_staging_runtime ? 1 : 0

  source = "../../modules/redis"

  name_prefix         = "socialos-staging"
  vpc_id              = module.network.vpc_id
  subnet_ids          = module.network.private_subnet_ids
  allowed_cidr_blocks = [module.network.vpc_cidr_block]
  node_type           = var.staging_redis_node_type

  tags = {
    LaunchStage = "private-beta"
  }
}

module "runtime" {
  count = var.enable_staging_runtime ? 1 : 0

  source = "../../modules/ecs_runtime"

  name_prefix   = "socialos-staging"
  vpc_id        = module.network.vpc_id
  subnet_ids    = module.network.public_subnet_ids
  api_image     = var.staging_api_image
  web_image     = var.staging_web_image
  desired_count = var.staging_desired_count

  api_environment = merge({
    ENVIRONMENT              = "staging"
    AUTH_MODE                = "clerk"
    MEDIA_STORAGE_PROVIDER   = "s3"
    S3_MEDIA_BUCKET          = module.media.bucket_id
    S3_MEDIA_REGION          = var.aws_region
    S3_MEDIA_PUBLIC_BASE_URL = module.media.media_public_base_url
    REDIS_URL                = module.redis[0].redis_url
  }, var.staging_api_environment)

  web_environment = merge({
    NEXT_PUBLIC_DEMO_MODE = "false"
  }, var.staging_web_environment)

  api_secrets = merge({
    DATABASE_URL = module.postgres[0].database_url_secret_arn
  }, var.staging_api_secret_arns)
  web_secrets         = var.staging_web_secret_arns
  secret_kms_key_arns = var.staging_secret_kms_key_arns
  task_policy_arns = [
    module.media_signer_iam.policy_arn,
  ]

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
