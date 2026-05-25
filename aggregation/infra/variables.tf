variable "aws_region" {
  type        = string
  description = "AWS region"
  default     = "ap-northeast-2"
}

variable "bucket_name" {
  type        = string
  description = "S3 bucket name (shared with future raw)"
  default     = "team-neki-log-production"
}

variable "function_name" {
  type        = string
  description = "Lambda function name"
  default     = "team-neki-log-aggregation-production-ingest"
}

variable "api_name" {
  type        = string
  description = "API Gateway name"
  default     = "team-neki-log-aggregation-production"
}

variable "alert_email" {
  type        = string
  description = "AWS Budgets 알림 수신 이메일"
}

variable "monthly_budget_usd" {
  type        = number
  description = "월 비용 상한 (USD)"
  default     = 5
}

variable "report_date_max_age_days" {
  type        = number
  description = "허용되는 report_date의 최대 과거 일수"
  default     = 7
}
