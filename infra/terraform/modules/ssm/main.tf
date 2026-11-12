# Parámetros cuyo valor pone una persona con la CLI (o deploy.sh). Terraform solo los crea
# con un valor de relleno y después no vuelve a tocar el valor.
# Los SecureString usan la llave administrada por AWS alias/aws/ssm (no se crean llaves KMS).
resource "aws_ssm_parameter" "manual" {
  for_each = var.manuales

  name        = "${var.prefijo}/${each.key}"
  type        = each.value.tipo
  description = each.value.descripcion
  value       = "CAMBIAR"

  lifecycle {
    ignore_changes = [value]
  }
}

# Parámetros no secretos cuyo valor sí administra Terraform.
resource "aws_ssm_parameter" "gestionado" {
  # No se filtran los vacíos aquí: muchos valores (IDs de otros módulos) se desconocen hasta el
  # apply, y filtrar por valor volvería desconocidas las llaves del for_each. En su lugar, la
  # precondición falla con un mensaje claro, porque SSM no acepta un String vacío.
  for_each = var.gestionados

  name  = "${var.prefijo}/${each.key}"
  type  = "String"
  value = each.value

  lifecycle {
    precondition {
      condition     = each.value != ""
      error_message = "El parámetro gestionado \"${each.key}\" está vacío; SSM no acepta valores vacíos. Quítalo del mapa o dale un valor."
    }
  }
}
