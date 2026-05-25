data "archive_file" "lambda_zip" {
  type        = "zip"
  source_dir  = "${path.module}/../src"
  output_path = "${path.module}/build/lambda.zip"
  excludes = [
    "__pycache__",
    "*.pyc",
    "*.dist-info",
    "*.egg-info",
  ]
}

resource "aws_lambda_function" "ingest" {
  function_name                  = var.function_name
  runtime                        = "python3.13"
  architectures                  = ["arm64"]
  memory_size                    = 256
  timeout                        = 10
  reserved_concurrent_executions = 2
  handler                        = "handler.lambda_handler"
  role                           = aws_iam_role.lambda.arn

  filename         = data.archive_file.lambda_zip.output_path
  source_code_hash = data.archive_file.lambda_zip.output_base64sha256

  environment {
    variables = {
      S3_BUCKET                = aws_s3_bucket.main.id
      S3_PREFIX                = "aggregation"
      REPORT_DATE_MAX_AGE_DAYS = tostring(var.report_date_max_age_days)
      LOG_LEVEL                = "INFO"
    }
  }

  depends_on = [
    aws_cloudwatch_log_group.lambda,
    aws_iam_role_policy.lambda,
  ]
}
