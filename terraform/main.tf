# ============================================================
# Infrastructure as Code — LocalStack (simula AWS gratis)
# ============================================================

terraform {
  required_version = ">= 1.5"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region                      = "us-east-1"
  access_key                  = "test"
  secret_key                  = "test"
  skip_credentials_validation = true
  skip_metadata_api_check     = true
  skip_requesting_account_id  = true

  endpoints {
    s3       = "http://localhost:4566"
    sqs      = "http://localhost:4566"
    sns      = "http://localhost:4566"
    iam      = "http://localhost:4566"
    dynamodb = "http://localhost:4566"
    ecr      = "http://localhost:4566"
    ecs      = "http://localhost:4566"
    ssm      = "http://localhost:4566"
  }
}

# ── S3 Bucket para backups ────────────────────────────────
resource "aws_s3_bucket" "backups" {
  bucket = "bookvault-backups"
}

resource "aws_s3_bucket_versioning" "backups" {
  bucket = aws_s3_bucket.backups.id
  versioning_configuration {
    status = "Enabled"
  }
}

# ── SQS Cola para eventos de auditoría ────────────────────
resource "aws_sqs_queue" "audit_events" {
  name                       = "bookvault-audit-events"
  message_retention_seconds  = 86400
  visibility_timeout_seconds = 30
}

# ── SNS Topic para alertas ────────────────────────────────
resource "aws_sns_topic" "alerts" {
  name = "bookvault-alerts"
}

# ── SSM Parameter Store para secretos ─────────────────────
resource "aws_ssm_parameter" "db_password" {
  name  = "/bookvault/db/password"
  type  = "SecureString"
  value = "super-secret-password-123"
}

resource "aws_ssm_parameter" "db_host" {
  name  = "/bookvault/db/host"
  type  = "String"
  value = "db"
}

# ── DynamoDB para feature flags ───────────────────────────
resource "aws_dynamodb_table" "feature_flags" {
  name         = "bookvault-feature-flags"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "feature_name"

  attribute {
    name = "feature_name"
    type = "S"
  }
}

# ── Outputs ───────────────────────────────────────────────
output "s3_bucket_name" {
  value = aws_s3_bucket.backups.id
}

output "sqs_queue_url" {
  value = aws_sqs_queue.audit_events.url
}

output "sns_topic_arn" {
  value = aws_sns_topic.alerts.arn
}
