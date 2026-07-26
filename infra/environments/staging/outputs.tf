output "media_bucket_name" {
  value = module.media.bucket_id
}

output "media_public_base_url" {
  value = module.media.media_public_base_url
}

output "cloudfront_distribution_id" {
  value = module.media.cloudfront_distribution_id
}

output "cloudfront_domain_name" {
  value = module.media.cloudfront_domain_name
}

output "media_signer_policy_arn" {
  value = module.media_signer_iam.policy_arn
}

output "budget_name" {
  value = module.budget.budget_name
}

output "ecr_repository_urls" {
  value = module.ecr.repository_urls
}

output "github_actions_deploy_role_arn" {
  value = module.github_oidc.deploy_role_arn
}

output "vpc_id" {
  value = module.network.vpc_id
}

output "public_subnet_ids" {
  value = module.network.public_subnet_ids
}

output "staging_alb_dns_name" {
  value = module.runtime.alb_dns_name
}

output "staging_ecs_cluster_name" {
  value = module.runtime.cluster_name
}

output "staging_api_service_name" {
  value = module.runtime.api_service_name
}

output "staging_web_service_name" {
  value = module.runtime.web_service_name
}

output "staging_task_role_arn" {
  value = module.runtime.task_role_arn
}
