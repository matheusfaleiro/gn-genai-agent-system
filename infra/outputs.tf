output "resource_group_name" {
  description = "Name of the resource group"
  value       = azurerm_resource_group.main.name
}

output "webapp_name" {
  description = "Name of the web app"
  value       = azurerm_linux_web_app.main.name
}

output "webapp_url" {
  description = "URL of the deployed API"
  value       = "https://${azurerm_linux_web_app.main.default_hostname}"
}
