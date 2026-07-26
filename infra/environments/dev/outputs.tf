output "media_bucket_name" {
  value = module.media.bucket_id
}

output "media_public_base_url" {
  value = module.media.media_public_base_url
}

output "cloudfront_distribution_id" {
  value = module.media.cloudfront_distribution_id
}
