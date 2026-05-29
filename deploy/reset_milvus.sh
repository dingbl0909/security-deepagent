#!/usr/bin/env bash
# 重置 MinIO + Milvus 数据卷（修复 MinIO 凭证不一致导致的 3/8 unhealthy）
#
# 典型日志：
#   The request signature we calculated does not match the signature you provided
#   find no available querycoord / datacoord
#
# 原因：MinIO 只在首次创建 volume 时写入 root 账号密码；之后改 .env 不会生效。
#
set -euo pipefail
cd "$(dirname "$0")/.."
cd deploy

PROJECT="${COMPOSE_PROJECT_NAME:-security-deepagent}"

echo "将删除以下 volume（PostgreSQL/Redis 不受影响）："
echo "  ${PROJECT}_minio_data"
echo "  ${PROJECT}_milvus_data"
echo ""
read -r -p "确认继续？[y/N] " ans
if [[ "${ans}" != "y" && "${ans}" != "Y" ]]; then
  echo "已取消"
  exit 0
fi

docker compose stop milvus minio
docker compose rm -f milvus minio 2>/dev/null || true

docker volume rm "${PROJECT}_minio_data" "${PROJECT}_milvus_data" 2>/dev/null || \
  docker volume rm deploy_minio_data deploy_milvus_data 2>/dev/null || true

echo "当前 MinIO 凭证（来自 .env）："
grep -E '^MINIO_ROOT_' .env || true

docker compose up -d minio
echo "等待 MinIO 就绪..."
sleep 5
docker compose up -d milvus etcd

echo ""
echo "等待 Milvus 启动（约 1–3 分钟），然后检查："
echo "  curl -s http://localhost:9091/healthz"
echo "期望输出：OK 或 HTTP 200（8/8 healthy）"
