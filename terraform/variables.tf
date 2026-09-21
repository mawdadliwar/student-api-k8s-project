variable "namespace" {
  default = "student-platform-tf"
}

variable "app_name" {
  default = "student-api"
}

variable "replica_count" {
  default = 2
}

variable "container_image" {
  default = "student-api:v1.0.0"
}

variable "container_port" {
  default = 5001
}

variable "service_port" {
  default = 80
}

variable "environment" {
  default = "production"
}
