variable "namespace" {
  type        = string
  description = "Kubernetes namespace name"
}

variable "app_name" {
  type        = string
  description = "Name of the application"
}

variable "replica_count" {
  type        = number
  description = "Number of deployment replicas"
  default     = 2
}

variable "container_image" {
  type        = string
  description = "Docker image for the application"
}

variable "container_port" {
  type        = number
  description = "Target port on the container"
  default     = 5001
}

variable "service_port" {
  type        = number
  description = "Exposed service port"
  default     = 80
}

variable "environment" {
  type        = string
  description = "Deployment environment"
  default     = "production"
}
