variable "prefijo" {
  description = "Ruta base de los parámetros, sin diagonal final. Ejemplo: /dsa/dev."
  type        = string
}

variable "manuales" {
  description = <<-EOT
    Parámetros cuyo valor NO administra Terraform: se crean con el valor CAMBIAR y después se ignoran sus cambios
    (los pone Juan Pablo con la CLI, o deploy.sh en el caso de image_tag). tipo: SecureString o String.
  EOT
  type = map(object({
    tipo        = string
    descripcion = string
  }))
  default = {}
}

variable "gestionados" {
  description = "Parámetros String cuyo valor sí administra Terraform (no son secretos). Mapa nombre => valor."
  type        = map(string)
  default     = {}
}
