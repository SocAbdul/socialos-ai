module "media" {
  source = "../../modules/media"

  name_prefix = "socialos-dev"
  bucket_name = var.media_bucket_name
}

