resource "kubernetes_namespace" "app_ns" {
  metadata {
    name = var.namespace
  }
}

resource "kubernetes_config_map" "app_config" {
  metadata {
    name      = "${var.app_name}-config"
    namespace = kubernetes_namespace.app_ns.metadata[0].name
  }

  data = {
    FLASK_ENV = var.environment
    PORT      = tostring(var.container_port)
    DB_PATH   = "/app/data/students.db"
  }
}

resource "kubernetes_secret" "app_secret" {
  metadata {
    name      = "${var.app_name}-secret"
    namespace = kubernetes_namespace.app_ns.metadata[0].name
  }

  data = {
    SECRET_KEY = "c3VwZXJzZWNyZXRrZXk="
  }
}

resource "kubernetes_persistent_volume_claim" "app_pvc" {
  metadata {
    name      = "${var.app_name}-pvc"
    namespace = kubernetes_namespace.app_ns.metadata[0].name
  }

  wait_until_bound = false

  spec {
    access_modes = ["ReadWriteOnce"]
    resources {
      requests = {
        storage = "1Gi"
      }
    }
  }
}

resource "kubernetes_deployment" "app_deployment" {
  metadata {
    name      = var.app_name
    namespace = kubernetes_namespace.app_ns.metadata[0].name
    labels = {
      app = var.app_name
    }
  }

  wait_for_rollout = false

  spec {
    replicas = var.replica_count

    selector {
      match_labels = {
        app = var.app_name
      }
    }

    template {
      metadata {
        labels = {
          app = var.app_name
        }
      }

      spec {
        container {
          name              = var.app_name
          image             = var.container_image
          image_pull_policy = "IfNotPresent"

          port {
            container_port = var.container_port
          }

          env_from {
            config_map_ref {
              name = kubernetes_config_map.app_config.metadata[0].name
            }
          }

          volume_mount {
            name       = "data-storage"
            mount_path = "/app/data"
          }
        }

        volume {
          name = "data-storage"
          persistent_volume_claim {
            claim_name = kubernetes_persistent_volume_claim.app_pvc.metadata[0].name
          }
        }
      }
    }
  }
}

resource "kubernetes_service" "app_service" {
  metadata {
    name      = "${var.app_name}-svc"
    namespace = kubernetes_namespace.app_ns.metadata[0].name
  }

  spec {
    selector = {
      app = var.app_name
    }

    port {
      port        = var.service_port
      target_port = var.container_port
    }

    type = "NodePort"
  }
}
