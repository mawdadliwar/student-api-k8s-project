module "kubernetes_platform" {
  source          = "./modules/kubernetes"
  namespace       = var.namespace
  app_name        = var.app_name
  replica_count   = var.replica_count
  container_image = var.container_image
  container_port  = var.container_port
  service_port    = var.service_port
  environment     = var.environment
}
