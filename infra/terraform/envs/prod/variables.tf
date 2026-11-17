variable "region" {
  description = "Región de AWS. El Learner Lab solo permite una."
  type        = string
  default     = "us-east-1"
}

variable "state_bucket" {
  description = "Bucket del estado de Terraform (output de bootstrap). Se usa para leer los outputs de shared."
  type        = string
}

variable "dominio" {
  description = "Dominio del proyecto, sin subdominio. Va en terraform.tfvars, que no se versiona."
  type        = string
}

variable "github_repo" {
  description = "Repo de GitHub como <org>/<repo>. La EC2 baja de ahí los archivos de deploy/ al crearse."
  type        = string
}

variable "image_registry" {
  description = "Registro de las imágenes, en minúsculas: ghcr.io/<org>/<repo>. Las imágenes son <registro>/backend y <registro>/mcp."
  type        = string

  validation {
    condition     = var.image_registry == lower(var.image_registry)
    error_message = "GHCR exige el nombre en minúsculas."
  }
}

variable "instance_type" {
  description = "Tipo de la instancia EC2 (x86_64)."
  type        = string
  default     = "t3.small"
}

variable "volume_gb" {
  description = "Disco raíz de la EC2, en GB."
  type        = number
  default     = 20
}

variable "auth_mode" {
  description = "dev: sin login real. cognito: el backend valida el JWT de Cognito."
  type        = string
  default     = "dev"

  validation {
    condition     = contains(["dev", "cognito"], var.auth_mode)
    error_message = "auth_mode debe ser dev o cognito."
  }
}

variable "s3_force_destroy" {
  description = "true: terraform destroy borra el bucket de archivos aunque no esté vacío."
  type        = bool
  default     = false
}
