# Sin correos no hay a quién avisar, así que no se crea el presupuesto.
resource "aws_budgets_budget" "este" {
  count = length(var.emails) > 0 ? 1 : 0

  name         = var.nombre
  budget_type  = "COST"
  time_unit    = "MONTHLY"
  limit_amount = tostring(var.limite_usd)
  limit_unit   = "USD"

  dynamic "notification" {
    for_each = var.umbrales_usd

    content {
      comparison_operator        = "GREATER_THAN"
      threshold                  = notification.value
      threshold_type             = "ABSOLUTE_VALUE"
      notification_type          = "ACTUAL"
      subscriber_email_addresses = var.emails
    }
  }
}
