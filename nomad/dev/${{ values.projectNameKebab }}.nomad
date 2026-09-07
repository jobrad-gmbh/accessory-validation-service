variable "namespace" {
  type    = string
  default = "${{ values.nomadNamespace }}"
}

variable "tag" {
  type = string
}

locals {
  opentelemetry_collector_version = "0.113.0"

  # Always set these Attributes, they are needed by opentelemetry-shipper
  attributes = {
    "nomad_datacenter" = "${NOMAD_DC}"
    "nomad_namespace"  = "${NOMAD_NAMESPACE}"
    "nomad_alloc_id"   = "${NOMAD_ALLOC_ID}"
    "nomad_job_name"   = "${NOMAD_JOB_NAME}"
    "nomad_group_name" = "${NOMAD_GROUP_NAME}"
    # meta data block (see below) (yes we need the round trip)
    "nomad_client_name" = "${NOMAD_META_CLIENT_NAME}"
  }
}

job "${{ values.projectNameKebab }}" {
  namespace = var.namespace

  group "${{ values.projectNameKebab }}-group" {
    count = 1

    network {
      mode = "bridge"
    }

    service {
      name = "${var.namespace}-${{ values.projectNameKebab }}"
      port = ${{ values.port }}

      connect {
        sidecar_service {
          proxy {
{%- if 'postgresql' in values.features %}
            upstreams {
              destination_name = "${var.namespace}-${{ values.projectNameKebab }}-postgres"
              local_bind_port  = 5432
            }
{%- endif %}
{%- if 'opentelemetry' in values.features %}
            upstreams {
              destination_name = "opentelemetry-shipper"
              local_bind_port  = 4317
            }
{%- endif %}
          }
        }
      }

      tags = [
        "traefik.enable=true",
        "traefik.consulcatalog.connect=true",
      ]


      check {
        name                     = "${{ values.projectNameKebab }} HTTP Health Check"
        type                     = "http"
        interval                 = "10s"
        path                     = "/health"
        timeout                  = "5s"
        address_mode             = "alloc"
        failures_before_critical = 3
      }
    }

    task "${{ values.projectNameKebab }}-task" {
      driver = "docker"
      leader = "true"

      resources {
        cpu    = ${{ values.nomadCpu }}
        memory = ${{ values.nomadMemory }}
      }

      config {
        image      = "ghcr.io/jobrad-gmbh/${{ values.projectNameKebab }}:${var.tag}"
        force_pull = true
      }

      vault {}

      template {
        destination = "secrets/env.conf"
        env         = true
        data        = <<-EOH
{%- if 'postgresql' in values.features %}
{% raw %}{{{% endraw %} with secret "nomad_kv_${var.namespace}/data/${{ values.projectNameFlat }}" {% raw %}}}{% endraw %}{%- endif %}
{%- if 'postgresql' in values.features %}
DATABASE_NAME="{% raw %}{{ .Data.data.POSTGRES_DB }}{% endraw %}"
DATABASE_USER="{% raw %}{{ .Data.data.POSTGRES_USER }}{% endraw %}"
DATABASE_PASSWORD="{% raw %}{{ .Data.data.POSTGRES_PASSWORD }}{% endraw %}"
DATABASE_HOST="{% raw %}{{ .Data.data.POSTGRES_HOST }}{% endraw %}"
 {{ end }}
{%- endif %}
EOH
      }


    }
{%- if 'opentelemetry' in values.features %}
    task "opentelemetry-collector" {
      driver = "docker"

      config {
        image = "otel/opentelemetry-collector-contrib:${local.opentelemetry_collector_version}"
        volumes = [
          "local/otel-collector-config.yaml:/etc/otelcol-contrib/config.yaml",
        ]
      }

      meta = {
        # We need to make the roundtrip here.
        CLIENT_NAME = "${node.unique.name}"
      }

      template {
        destination = "local/otel-collector-config.yaml"
        data = yamlencode({
          # inputs
          receivers = {
            prometheus_simple = {
              collection_interval = "10s"
              endpoint            = "localhost:${{ values.port }}"
              metrics_path        = "/metrics/"
            }
            "filelog/stdout" = {
              include_file_name = true
              include_file_path = false
              include = [
                "${NOMAD_ALLOC_DIR}/logs/${{ values.projectNameKebab }}-task.stdout.*",
              ]
            }
            "filelog/stderr" = {
              include = [
                "${NOMAD_ALLOC_DIR}/logs/${{ values.projectNameKebab }}-task.stderr.*",
              ]
            }
          }
          # processors
          processors = {
            "metricstransform/${{ values.projectNameKebab }}" = {
              transforms = [
                {
                  # prefix everything with ${{ values.projectNameKebab }}
                  include    = "^(.*)$$"
                  match_type = "regexp"
                  action     = "update"
                  new_name   = "${{ values.projectNameKebab }}_$$1"
                }
              ]
            }
            attributes = {
              actions = [for k, v in local.attributes : {
                key    = k
                value  = v
                action = "insert"
              }]
            }
            "transform/timestamp" = {
              error_mode = "ignore"
              log_statements = [{
                context = "log"
                statements = [
                  "set(time_unix_nano, observed_time_unix_nano)"
                ]
              }]
            }
          }
          # outputs
          exporters = {
            otlphttp = {
              endpoint = "http://localhost:4317"
              tls = {
                insecure = true
              }
            }
          }
          # wiring
          service = {
            pipelines = {
              logs = {
                receivers = [
                  "filelog/stdout",
                  "filelog/stderr",
                ]
                processors = [
                  "transform/timestamp",
                  "attributes",
                ]
                exporters = [
                  "otlphttp",
                ]
              }
              metrics = {
                receivers = [
                  "prometheus_simple",
                ]
                processors = [
                  "attributes",
                  "metricstransform/test-service-python",
                ]
                exporters = [
                  "otlphttp",
                ]
              }
            }
          }
        })
      }
    }
{%- endif %}
  }
}
