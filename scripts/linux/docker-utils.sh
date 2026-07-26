#!/usr/bin/env bash

# Remove only containers created by the repository's previous Compose layout.
remove_legacy_backend_containers() {
  local name expected_service container_id project service

  for entry in "rag-api:api" "rag-qdrant:qdrant"; do
    name="${entry%%:*}"
    expected_service="${entry##*:}"
    container_id="$(docker ps -aq --filter "name=^/${name}$" | head -n 1)"

    [[ -z "$container_id" ]] && continue

    project="$(docker inspect "$container_id" \
      --format '{{index .Config.Labels "com.docker.compose.project"}}')"
    service="$(docker inspect "$container_id" \
      --format '{{index .Config.Labels "com.docker.compose.service"}}')"

    if [[ "$project" != "backend" || "$service" != "$expected_service" ]]; then
      echo "Error: container '$name' belongs to another Docker project."
      echo "Stop or rename it manually before starting Libra Assist."
      return 1
    fi

    echo "Removing legacy container: $name"
    docker rm -f "$container_id" >/dev/null
  done
}
