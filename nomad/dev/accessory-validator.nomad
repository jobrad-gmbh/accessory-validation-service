variable "namespace" {
  type    = string
  default = "pto"
}

variable "tag" {
  type = string
}

job "accessory-validator" {
  namespace = var.namespace

  group "accessory-validator-group" {
    count = 1

    network {
      mode = "bridge"
    }

    service {
      name = "${var.namespace}-accessory-validator"
      port = 8000

      connect {
        sidecar_service {}
      }

      tags = [
        "traefik.enable=true",
        "traefik.consulcatalog.connect=true",
      ]

      check {
        name                     = "accessory-validator HTTP Health Check"
        type                     = "http"
        interval                 = "10s"
        path                     = "/health"
        timeout                  = "5s"
        address_mode             = "alloc"
        failures_before_critical = 3
      }
    }

    task "accessory-validator-task" {
      driver = "docker"
      leader = true

      resources {
        cpu    = 256
        memory = 512
      }

      config {
        image      = "ghcr.io/jobrad-gmbh/accessory-validator:${var.tag}"
        force_pull = true
      }

      vault {}

      template {
        destination = "secrets/env.conf"
        env         = true
        data        = <<-EOH
{{ with secret "nomad_kv_${var.namespace}/data/accessoryvalidator" }}
SEARXNG_BASE_URL="{{ .Data.data.SEARXNG_BASE_URL }}"
LLM_BASE_URL="{{ .Data.data.LLM_BASE_URL }}"
LLM_API_KEY="{{ .Data.data.LLM_API_KEY }}"
LLM_MODEL="{{ .Data.data.LLM_MODEL }}"
{{ end }}
EOH
      }
    }
  }
}
