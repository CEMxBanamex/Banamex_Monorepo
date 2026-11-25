variable "nombre" {
  description = "Prefijo de los nombres de los recursos."
  type        = string
  default     = "dsa"
}

variable "env" {
  description = "Ambiente: dev o prod. Va en la etiqueta Env, que usa SSM Run Command para elegir la instancia."
  type        = string
}

variable "subnet_id" {
  description = "Subred pública donde vive la instancia."
  type        = string
}

variable "security_group_id" {
  description = "Security group de la instancia."
  type        = string
}

variable "instance_type" {
  description = "Tipo de instancia (x86_64)."
  type        = string
  default     = "t3.small"
}

variable "volume_gb" {
  description = "Tamaño del disco raíz gp3, en GB."
  type        = number
  default     = 20
}

variable "runner" {
  description = "true en dev: agrega la etiqueta Runner=true (aloja el runner self-hosted de GitHub Actions)."
  type        = bool
  default     = false
}

variable "user_data" {
  description = "Script de arranque ya renderizado. null mientras no exista deploy/user-data.sh (Fase 4)."
  type        = string
  default     = null
}

variable "instance_profile_name" {
  description = "Perfil de instancia existente. En Learner Lab no se pueden crear roles: se usa LabInstanceProfile."
  type        = string
  default     = "LabInstanceProfile"
}
