variable "nombre" {
  description = "Prefijo de los nombres de los recursos."
  type        = string
  default     = "dsa"
}

variable "vpc_id" {
  description = "VPC donde se crean los security groups."
  type        = string
}

variable "ambientes" {
  description = "Un security group de EC2 por ambiente. allowed_cidrs: quién puede llegar al 443 (HTTPS de la API)."
  type = map(object({
    allowed_cidrs = list(string)
  }))
}

variable "db_allowed_cidrs" {
  description = "CIDR que pueden llegar al 5432 de RDS además de las EC2. Lista vacía cuando la base sea privada."
  type        = list(string)
  default     = ["0.0.0.0/0"]
}
