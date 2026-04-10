variable "cloudflare_api_token" {
  type        = string
  description = "Cloudflare API token."
  sensitive   = true
  ephemeral   = true
}

provider "cloudflare" {
  api_token = var.cloudflare_api_token
}
