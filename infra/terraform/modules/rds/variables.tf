variable "nombre" {
  description = "Prefijo de los nombres de los recursos."
  type        = string
  default     = "dsa"
}

variable "subnet_ids" {
  description = "Subredes del subnet group (las públicas mientras la base sea pública)."
  type        = list(string)
}

variable "security_group_id" {
  description = "Security group de RDS."
  type        = string
}

variable "engine_version" {
  description = "Versión de PostgreSQL. Con solo la mayor, AWS elige la menor vigente."
  type        = string
  default     = "16"
}

variable "instance_class" {
  description = "Clase de la instancia."
  type        = string
  default     = "db.t4g.micro"
}

variable "allocated_storage" {
  description = "Disco en GB (gp3)."
  type        = number
  default     = 20
}

variable "master_username" {
  description = "Usuario maestro. La contraseña la administra RDS en Secrets Manager."
  type        = string
  default     = "dsa_admin"
}

variable "db_publica" {
  description = "true: la base tiene IP pública (temporal, para DBeaver/pgAdmin del equipo). false: solo desde la VPC."
  type        = bool
  default     = true
}

variable "backup_retention_days" {
  description = "Días de respaldo automático."
  type        = number
  default     = 1
}
