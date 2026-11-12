output "budget_name" {
  description = "Nombre del presupuesto, o null si no se creó."
  value       = one(aws_budgets_budget.este[*].name)
}
