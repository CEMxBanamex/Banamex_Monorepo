variable "nombre" {
  description = "Nombre del user pool."
  type        = string
  default     = "dsa"
}

variable "grupos" {
  description = "Grupos del user pool, uno por rol del producto."
  type        = list(string)
  default     = ["analista", "administrador"]
}

variable "callback_urls" {
  description = "URLs del frontend a las que Cognito regresa después del login."
  type        = list(string)
}

variable "logout_urls" {
  description = "URLs del frontend a las que Cognito regresa después del logout."
  type        = list(string)
}

variable "dominio_prefijo" {
  description = "Prefijo del dominio de la interfaz de login alojada por Cognito. null: no se crea."
  type        = string
  default     = null
}
