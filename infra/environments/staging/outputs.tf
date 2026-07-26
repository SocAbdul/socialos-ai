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

output "private_subnet_ids" {
  value = module.network.private_subnet_ids
}

output "staging_alb_dns_name" {
  value = try(module.runtime[0].alb_dns_name, null)
}

output "staging_ecs_cluster_name" {
  value = try(module.runtime[0].cluster_name, null)
}

output "staging_api_service_name" {
  value = try(module.runtime[0].api_service_name, null)
}

output "staging_web_service_name" {
  value = try(module.runtime[0].web_service_name, null)
}

output "staging_api_task_definition_arn" {
  value = try(module.runtime[0].api_task_definition_arn, null)
}

output "staging_web_task_definition_arn" {
  value = try(module.runtime[0].web_task_definition_arn, null)
}

output "staging_task_role_arn" {
  value = try(module.runtime[0].task_role_arn, null)
}

output "staging_service_security_group_id" {
  value = try(module.runtime[0].service_security_group_id, null)
}

output "staging_postgres_endpoint" {
  value = try(module.postgres[0].endpoint, null)
}

output "staging_database_url_secret_arn" {
  value = try(module.postgres[0].database_url_secret_arn, null)
}

output "staging_redis_endpoint" {
  value = try(module.redis[0].primary_endpoint_address, null)
}
