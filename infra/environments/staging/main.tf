module "media" {
  source = "../../modules/media"

  name_prefix          = "socialos-staging"
  bucket_name          = var.media_bucket_name
  cors_allowed_origins = var.media_cors_allowed_origins

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
