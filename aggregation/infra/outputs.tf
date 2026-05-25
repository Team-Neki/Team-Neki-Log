output "api_endpoint" {
  description = "POST endpoint for GA4 daily report ingestion"
  value       = "${aws_apigatewayv2_api.main.api_endpoint}/aggregations/ga4-daily-report"
}

output "bucket_name" {
  description = "S3 bucket name"
  value       = aws_s3_bucket.main.id
}

output "lambda_function_name" {
  description = "Lambda function name"
  value       = aws_lambda_function.ingest.function_name
}

output "log_group_name" {
  description = "CloudWatch Log Group for Lambda"
  value       = aws_cloudwatch_log_group.lambda.name
}
