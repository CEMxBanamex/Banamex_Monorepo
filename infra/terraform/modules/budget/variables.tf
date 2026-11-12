variable "nombre" {
  description = "Nombre del presupuesto."
  type        = string
  default     = "dsa-mensual"
}

variable "limite_usd" {
  description = "Límite mensual en USD."
  type        = number
}

variable "umbrales_usd" {
  description = "Montos en USD (gasto real) que disparan una alerta por correo."
  type        = list(number)
}

variable "emails" {
  description = "Correos que reciben las alertas. Si está vacía, no se crea el presupuesto."
  type        = list(string)
}
