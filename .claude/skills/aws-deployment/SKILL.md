---
name: aws-deployment
description: Deploy the chatbot on AWS (ECS/Fargate, ALB, S3/CloudFront, Secrets Manager, RDS). Use when changing AWS infra, production deploy, networking, or cloud secrets.
---

# AWS Deployment

## Target shape

- **API + worker**: ECS Fargate behind an ALB. Autoscaling on CPU and queue depth.
- **Frontend**: S3 + CloudFront (or same ALB if SSR).
- **Data**: RDS Postgres or Supabase (hosted). Redis on ElastiCache if used.
- **Secrets**: AWS Secrets Manager or SSM. Task role, not long-lived keys on disk.
- **Uploads / raw docs**: S3. Signed URLs; buckets are private.

## Networking

- Public ALB, private tasks. Egress for LLM APIs.
- Restrict security groups: ALB → tasks :8000, tasks → db :5432, tasks → redis :6379.

## Config

- One task definition family per service. Image tag = git SHA.
- Health check path `/health`. Deregistration delay long enough for in-flight SSE to finish or drain.

## Observability

- CloudWatch logs + OpenTelemetry/Langfuse from the app (see `observability`).
- Alarms: 5xx, CPU, task restarts, DLQ depth, LLM error rate.

## Do not

- Put the database in a public subnet.
- Use IAM user access keys in the frontend.
- Open SSH to the world “just for debug”.
---
