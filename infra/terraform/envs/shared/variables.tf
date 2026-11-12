variable "region" {
  description = "Región de AWS. El Learner Lab solo permite una."
  type        = string
  default     = "us-east-1"
}

variable "dominio" {
  description = "Dominio del proyecto, sin subdominio (ejemplo: midominio.com). Va en terraform.tfvars, que no se versiona."
  type        = string
}

variable "allowed_cidrs_dev" {
  description = "CIDR que pueden llegar al HTTPS de la API de dev (IP del equipo mientras AUTH_MODE=dev)."
  type        = list(string)
}

variable "allowed_cidrs_prod" {
  description = "CIDR que pueden llegar al HTTPS de la API de prod. Con Cognito activo: [\"0.0.0.0/0\"]."
  type        = list(string)
}

variable "db_publica" {
  description = "true: RDS con IP pública (temporal, hasta el cierre). false: solo desde la VPC."
  type        = bool
  default     = true
}

variable "db_allowed_cidrs" {
  description = "CIDR que pueden llegar al 5432 de RDS además de las EC2. En el cierre: []."
  type        = list(string)
  default     = ["0.0.0.0/0"]
}

variable "presupuesto_limite_usd" {
  description = "Límite mensual del presupuesto, en USD."
  type        = number
  default     = 20
}

variable "presupuesto_umbrales_usd" {
  description = "Montos de gasto real, en USD, que mandan alerta por correo."
  type        = list(number)
  default     = [8, 14, 20]
}

variable "presupuesto_emails" {
  description = "Correos que reciben las alertas. Vacía: no se crea el presupuesto."
  type        = list(string)
  default     = []
}

variable "enable_cognito" {
  description = "true: crea el user pool de Cognito (última semana del proyecto)."
  type        = bool
  default     = false
}

variable "cognito_dominio_prefijo" {
  description = "Prefijo del dominio de login alojado por Cognito (único en la región). null: no se crea."
  type        = string
  default     = null
}
