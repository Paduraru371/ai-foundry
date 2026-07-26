function Remove-LegacyBackendContainers {
    $LegacyContainers = @(
        @{ Name = "rag-api"; Service = "api" },
        @{ Name = "rag-qdrant"; Service = "qdrant" }
    )

    foreach ($Legacy in $LegacyContainers) {
        $NameFilter = "name=^/$($Legacy.Name)`$"
        $ContainerId = (& docker ps -aq --filter $NameFilter | Select-Object -First 1)
        if ([string]::IsNullOrWhiteSpace($ContainerId)) {
            continue
        }

        $Container = (& docker inspect $ContainerId | Out-String | ConvertFrom-Json)[0]
        $Project = $Container.Config.Labels.'com.docker.compose.project'
        $Service = $Container.Config.Labels.'com.docker.compose.service'

        if ($Project -ne "backend" -or $Service -ne $Legacy.Service) {
            throw "Container '$($Legacy.Name)' belongs to another Docker project. Stop or rename it manually."
        }

        Write-Host "Removing legacy container: $($Legacy.Name)"
        & docker rm -f $ContainerId | Out-Null
        if ($LASTEXITCODE -ne 0) {
            throw "Could not remove legacy container '$($Legacy.Name)'."
        }
    }
}
