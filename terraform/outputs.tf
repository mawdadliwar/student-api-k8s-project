output "namespace" {
  value = module.kubernetes_platform.namespace
}

output "service_name" {
  value = module.kubernetes_platform.service_name
}

output "deployment_name" {
  value = module.kubernetes_platform.deployment_name
}

output "replica_count" {
  value = module.kubernetes_platform.active_replicas
}
