output "namespace" {
  value = kubernetes_namespace.app_ns.metadata[0].name
}

output "service_name" {
  value = kubernetes_service.app_service.metadata[0].name
}

output "deployment_name" {
  value = kubernetes_deployment.app_deployment.metadata[0].name
}

output "active_replicas" {
  value = kubernetes_deployment.app_deployment.spec[0].replicas
}
