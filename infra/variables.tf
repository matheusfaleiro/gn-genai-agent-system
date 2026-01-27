variable "location" {
  description = "Azure region for resources"
  type        = string
  default     = "eastus"
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  default     = "dev"

  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be dev, staging, or prod."
  }
}

variable "project_name" {
  description = "Project name used for resource naming"
  type        = string
  default     = "ticketing-api"
}

variable "sku_name" {
  description = "App Service plan SKU (B1, B2, S1, P1v2, etc.)"
  type        = string
  default     = "B1"
}

variable "python_version" {
  description = "Python version for the web app"
  type        = string
  default     = "3.11"
}

variable "always_on" {
  description = "Keep the app always loaded (recommended for prod)"
  type        = bool
  default     = false
}
