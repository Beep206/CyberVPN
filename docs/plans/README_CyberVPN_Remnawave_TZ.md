# CyberVPN: комплект ТЗ и production-схема Remnawave 2.8.0

В комплект входят:

1. [`TZ_Codex_Task1_Premium_Smart_RU_Remnawave_2_8_0.md`](TZ_Codex_Task1_Premium_Smart_RU_Remnawave_2_8_0.md) - нормативное ТЗ по исправлению и унификации Premium Smart RU.
2. [`TZ_Codex_Task2_SPB_Default_With_DE_Exceptions_Remnawave_2_8_0.md`](TZ_Codex_Task2_SPB_Default_With_DE_Exceptions_Remnawave_2_8_0.md) - нормативное ТЗ нового тарифа с SPB по умолчанию и DE-маршрутом для Antifilter/vendor/custom prefixes.
3. [`CYBERVPN_PREMIUM_SMART_RU_CURRENT_PRODUCTION_ARCHITECTURE.md`](../architecture/CYBERVPN_PREMIUM_SMART_RU_CURRENT_PRODUCTION_ARCHITECTURE.md) - подробный internal-only snapshot фактически развернутых настроек, границ доказательства, диагностики и rollback.
4. [`CyberVPN_Remnawave_2_8_0_TZ_manifest.json`](CyberVPN_Remnawave_2_8_0_TZ_manifest.json) - размеры, число строк и SHA-256 файлов комплекта.

ТЗ описывают требуемое поведение и не являются доказательством production-развертывания. Для текущего состояния сначала читать архитектурный snapshot, затем сверять его с final generated subscription и загруженным runtime. На текущем production Premium Smart RU имеет подтвержденные generated INCY/HAPP paths, восемь RAW/XHTTP transport paths и isolated DE/NL + SPB/Moscow failover canary: только exact backend-owned JSON marker включает canary, stable users остаются на static template. Final Remnawave-generated canary прошел normal, primary-down, all-down BLOCK и recovery; отдельно остается физическая phone-side INCY TUN проверка. Task2 активирован после authoritative 13-community Antifilter artifact, DNS-only A ingress, dedicated RAW/XHTTP listeners, изолированного IPv6 bridge и production route matrix. Cloudflare token и exact A record проверены read-only, но Terraform import записи ожидает отдельные AWS/S3 remote-state credentials. Физическая Task2 device-side проверка также остается внешним evidence.

Документы намеренно не содержат customer credentials, subscription URLs, Reality keys, bridge secrets, invite codes и PII. Исходные ТЗ восстановлены в текущую рабочую папку из результатов исследования и приложенной production/target-архитектуры, поскольку первоначальные ссылки указывали на временные sandbox paths.
