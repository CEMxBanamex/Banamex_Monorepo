variable "nombre" {
  description = "Prefijo del nombre del bucket."
  type        = string
  default     = "dsa"
}

variable "env" {
  description = "Ambiente: dev o prod."
  type        = string
}

variable "allowed_origins" {
  description = "Orígenes del frontend que pueden subir y leer con URL prefirmada (CORS: PUT y GET)."
  type        = list(string)
}

variable "force_destroy" {
  description = "true: terraform destroy borra el bucket aunque tenga archivos."
  type        = bool
  default     = false
}
