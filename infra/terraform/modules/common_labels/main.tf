locals {
  labels = merge(
    {
      project     = var.project
      environment = var.environment
      managed_by  = var.managed_by
    },
    var.extra,
  )
}
