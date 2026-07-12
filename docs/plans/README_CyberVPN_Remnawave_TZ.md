# CyberVPN: комплект ТЗ и production-схема Remnawave 2.8.0

В комплект входят:

1. [`TZ_Codex_Task1_Premium_Smart_RU_Remnawave_2_8_0.md`](TZ_Codex_Task1_Premium_Smart_RU_Remnawave_2_8_0.md) - нормативное ТЗ по исправлению и унификации Premium Smart RU.
2. [`TZ_Codex_Task2_SPB_Default_With_DE_Exceptions_Remnawave_2_8_0.md`](TZ_Codex_Task2_SPB_Default_With_DE_Exceptions_Remnawave_2_8_0.md) - нормативное ТЗ нового тарифа с SPB по умолчанию и DE-маршрутом для Antifilter/vendor/custom prefixes.
3. [`CYBERVPN_PREMIUM_SMART_RU_CURRENT_PRODUCTION_ARCHITECTURE.md`](../architecture/CYBERVPN_PREMIUM_SMART_RU_CURRENT_PRODUCTION_ARCHITECTURE.md) - подробный internal-only snapshot фактически развернутых настроек, границ доказательства, диагностики и rollback.
4. [`CyberVPN_Remnawave_2_8_0_TZ_manifest.json`](CyberVPN_Remnawave_2_8_0_TZ_manifest.json) - размеры, число строк и SHA-256 файлов комплекта.

ТЗ описывают требуемое поведение и не являются доказательством production-развертывания. Для текущего состояния сначала читать архитектурный snapshot, затем сверять его с final generated subscription и загруженным runtime. На момент snapshot Premium Smart RU имеет подтвержденный server/generated XHTTP path, но phone-side INCY TUN и надежность Moscow RAW остаются открытыми. Task2 остается fail-closed до появления authoritative Antifilter BGP manifest, DNS, listener/profile и полной runtime route matrix.

Документы намеренно не содержат customer credentials, subscription URLs, Reality keys, bridge secrets, invite codes и PII. Исходные ТЗ восстановлены в текущую рабочую папку из результатов исследования и приложенной production/target-архитектуры, поскольку первоначальные ссылки указывали на временные sandbox paths.
