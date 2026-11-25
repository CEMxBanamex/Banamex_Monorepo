variable "nombre" {
  description = "Prefijo de los nombres de los recursos."
  type        = string
  default     = "dsa"
}

variable "cidr_vpc" {
  description = "Bloque /16 de la VPC."
  type        = string
  default     = "10.20.0.0/16"
}
