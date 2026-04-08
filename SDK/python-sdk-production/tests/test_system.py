import pytest

from remnawave.models import (
    GetBandwidthStatsResponseDto,
    GetMetadataResponseDto,
    GetNodesStatisticsResponseDto,
    GetRecapResponseDto,
    GetStatsResponseDto,
    GetNodesMetricsResponseDto,
    GetRemnawaveHealthResponseDto,
)


class TestSystemStatistics:
    """Тесты для получения статистики системы"""
    
    @pytest.mark.asyncio
    async def test_get_stats(self, remnawave):
        """Тест получения общей статистики"""
        stats = await remnawave.system.get_stats()
        assert isinstance(stats, GetStatsResponseDto)
        assert hasattr(stats, 'timestamp')
        assert hasattr(stats, 'uptime')
    
    @pytest.mark.asyncio
    async def test_get_bandwidth_stats(self, remnawave):
        """Тест получения статистики по полосе пропускания"""
        bandwidth_stats = await remnawave.system.get_bandwidth_stats()
        assert isinstance(bandwidth_stats, GetBandwidthStatsResponseDto)
        assert hasattr(bandwidth_stats, 'current_year')

    @pytest.mark.asyncio
    async def test_get_metadata(self, remnawave):
        """Тест получения системной метаинформации"""
        metadata = await remnawave.system.get_metadata()
        assert isinstance(metadata, GetMetadataResponseDto)
        assert metadata.version
        assert metadata.build.time
        assert metadata.git.backend.commit_sha

    @pytest.mark.asyncio
    async def test_get_recap(self, remnawave):
        """Тест получения общего recap по системе"""
        recap = await remnawave.system.get_recap()
        assert isinstance(recap, GetRecapResponseDto)
        assert hasattr(recap, 'total')
        assert hasattr(recap, 'this_month')
    
    @pytest.mark.asyncio
    async def test_get_nodes_statistics(self, remnawave):
        """Тест получения статистики по нодам"""
        nodes_statistics = await remnawave.system.get_nodes_statistics()
        assert isinstance(nodes_statistics, GetNodesStatisticsResponseDto)
        assert hasattr(nodes_statistics, 'last_seven_days')


class TestSystemMonitoring:
    """Тесты для мониторинга системы"""
    
    @pytest.mark.asyncio
    async def test_get_nodes_metrics(self, remnawave):
        """Тест получения метрик нод"""
        nodes_metrics = await remnawave.system.get_nodes_metrics()
        assert isinstance(nodes_metrics, GetNodesMetricsResponseDto)
        assert hasattr(nodes_metrics, 'nodes')
        assert isinstance(nodes_metrics.nodes, list)
        
        if nodes_metrics.nodes:  # Если список не пустой
            node = nodes_metrics.nodes[0]
            assert hasattr(node, 'node_uuid')
            assert hasattr(node, 'node_name')
            assert hasattr(node, 'country_emoji')
            assert hasattr(node, 'provider_name')
            assert hasattr(node, 'users_online')
            assert hasattr(node, 'inbounds_stats')
            assert hasattr(node, 'outbounds_stats')
    
    @pytest.mark.asyncio
    async def test_get_health(self, remnawave):
        """Тест получения состояния здоровья системы"""
        health = await remnawave.system.get_health()
        assert isinstance(health, GetRemnawaveHealthResponseDto)
        assert hasattr(health, 'runtime_metrics')
        assert isinstance(health.runtime_metrics, list)
