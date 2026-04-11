import { defaultLocale } from '@/i18n/config';
import {
  localizeSeoReadingTime,
  resolveSeoPriorityMarketLocale,
  seoPriorityMarketLocales,
} from '@/content/seo/market-localization';
import type { SeoArticleEntry, SeoDeviceEntry } from '@/content/seo/types';

type LocalizedArticleCopy = Partial<
  Pick<
  SeoArticleEntry,
  'badge' | 'title' | 'description' | 'heroPoints' | 'sections' | 'relatedLinks' | 'ctaLinks'
  >
>;

type LocalizedDeviceCopy = LocalizedArticleCopy &
  Partial<Pick<SeoDeviceEntry, 'featureList' | 'offers'>>;

type LocalizedEntryRecord<T> = Partial<Record<SeoDetailLocale, T>>;

export const seoDetailLocales = [...seoPriorityMarketLocales] as const;

type SeoDetailLocale = (typeof seoDetailLocales)[number];

function resolveSeoDetailLocale(locale?: string): SeoDetailLocale {
  const resolvedLocale = resolveSeoPriorityMarketLocale(locale);

  if (seoDetailLocales.includes(resolvedLocale as SeoDetailLocale)) {
    return resolvedLocale as SeoDetailLocale;
  }

  return defaultLocale;
}

export function localizeArticleEntry(
  base: SeoArticleEntry,
  localizedContent: LocalizedEntryRecord<LocalizedArticleCopy>,
  locale?: string,
): SeoArticleEntry {
  const resolvedLocale = resolveSeoDetailLocale(locale);
  const localized = localizedContent[resolvedLocale];

  if (!localized) {
    return {
      ...base,
      readingTime: localizeSeoReadingTime(base.readingTime, locale),
    };
  }

  return {
    ...base,
    ...localized,
    readingTime: localizeSeoReadingTime(base.readingTime, resolvedLocale),
  };
}

export function localizeDeviceEntry(
  base: SeoDeviceEntry,
  localizedContent: LocalizedEntryRecord<LocalizedDeviceCopy>,
  locale?: string,
): SeoDeviceEntry {
  const resolvedLocale = resolveSeoDetailLocale(locale);
  const localized = localizedContent[resolvedLocale];

  if (!localized) {
    return {
      ...base,
      readingTime: localizeSeoReadingTime(base.readingTime, locale),
    };
  }

  return {
    ...base,
    ...localized,
    readingTime: localizeSeoReadingTime(base.readingTime, resolvedLocale),
  };
}

export const GUIDE_DETAIL_LOCALIZATION: Record<string, LocalizedEntryRecord<LocalizedArticleCopy>> = {
  'how-to-bypass-dpi-with-vless-reality': {
    'ru-RU': {
      badge: 'Обход DPI',
      title: 'Как обходить DPI с VLESS Reality без лишней задержки',
      description:
        'Настройте Reality-профиль, который переживает агрессивных провайдеров, не раздувает handshake и остаётся пригодным для обычного веба, стриминга и мобильного трафика.',
      heroPoints: [
        'Маршрут выглядит как обычный TLS-трафик для большинства фильтрующих сетей.',
        'Накладные расходы остаются низкими даже на мобильных и роуминговых каналах.',
        'Нет зависимости от хрупких цепочек обфускации, которые ломаются после одной policy-обновы.',
      ],
      sections: [
        {
          title: 'Начинайте с правдоподобной точки транспорта',
          paragraphs: [
            'Выбирайте Reality target, у которого уже есть стабильная ротация сертификатов и нормальная публичная репутация. Цель здесь не экзотика, а маскировка.',
            'Держите по одной входной точке на регион, чтобы было видно, какой маршрут реально начал деградировать до того, как вы начнёте крутить параметры.',
          ],
          bullets: [
            'Фиксируйте SNI, fingerprint и flow-настройки на всём клиентском парке.',
            'Разделяйте high-risk маршруты обхода и обычные performance-маршруты.',
            'Подготовьте fallback-профиль до массового rollout на устройства.',
          ],
        },
        {
          title: 'Подгоняйте профиль под агрессивные домашние и мобильные сети',
          paragraphs: [
            'Reality лучше всего работает, когда остальная часть профиля скучная и предсказуемая. Не добавляйте лишние трюки, если у вас нет захвата пакетов, доказывающего пользу.',
            'Если регион начал проседать, проверяйте DNS, TLS fingerprinting и shaping по очереди, а не меняйте всё сразу.',
          ],
          bullets: [
            'Используйте resolver path, который соответствует выбранному региону.',
            'Держите MTU консервативным на мобильных операторах с жёсткой фрагментацией.',
            'После каждого изменения смотрите на success rate, а не на случайные отзывы из чата.',
          ],
        },
        {
          title: 'Эксплуатируйте маршрут как инцидентную поверхность',
          paragraphs: [
            'Обход блокировок — это операционная дисциплина. Каждый сломанный маршрут должен иметь понятный rollback и повторяемую процедуру, а не существовать как разовая настройка.',
            'Сводите в один цикл данные поддержки, типы устройств и наблюдения по packet loss, чтобы слабые маршруты умирали быстро.',
          ],
          bullets: [
            'Следите за ростом handshake failures по ASN.',
            'Держите чистый backup path прямо в download bundle.',
            'Публикуйте status-обновления сразу, когда маршрут уходит в ротацию.',
          ],
        },
      ],
      relatedLinks: [
        {
          label: 'Документация по протоколам',
          href: '/docs',
          description: 'Проверьте базовую транспортную модель перед изменением клиентских профилей.',
        },
        {
          label: 'Позиция по безопасности',
          href: '/security',
          description: 'Посмотрите, на каких hardening-допущениях держится маршрут.',
        },
        {
          label: 'Независимые аудиты',
          href: '/audits',
          description: 'Поймите, какие evidence должны существовать до доверия новому маршруту.',
        },
      ],
      ctaLinks: [
        {
          label: 'Сравнить тарифы',
          href: '/pricing',
          description: 'Выберите тариф с запасом по трафику и числу устройств.',
          seoCta: 'guide_pricing',
          seoZone: 'guides_content',
        },
        {
          label: 'Скачать клиенты',
          href: '/download',
          description: 'Получите клиенты для Android, iOS, desktop и стеков на базе sing-box.',
          seoCta: 'guide_download',
          seoZone: 'guides_content',
        },
        {
          label: 'Открыть trust center',
          href: '/trust',
          description: 'Проверьте политику логирования, инфраструктурный контроль и обработку abuse-сценариев.',
          seoCta: 'guide_trust',
          seoZone: 'guides_content',
        },
      ],
    },
    'zh-CN': {
      badge: '绕过 DPI',
      title: '如何用 VLESS Reality 绕过 DPI 且不过度增加延迟',
      description:
        '部署一个能够穿过高压 ISP、保持握手特征克制且仍适合日常浏览、流媒体与移动网络使用的 Reality 配置。',
      heroPoints: [
        '对大多数过滤网络来说，这条路径更像普通 TLS 流量。',
        '即使在移动链路和漫游环境中，额外开销也保持较低。',
        '不依赖一串脆弱的混淆技巧，避免策略一变就整体失效。',
      ],
      sections: [
        {
          title: '先选择可信且自然的传输目标',
          paragraphs: [
            '优先选择本身就有稳定证书轮换和广泛公共信任的 Reality target。这里要追求的是伪装质量，而不是花哨。',
            '每个区域保留一个清晰入口点，这样当路由被限速时，你能先定位问题，再决定要不要轮换。',
          ],
          bullets: [
            '在整个客户端群组中保持 SNI、fingerprint 和 flow 设置一致。',
            '把高风险抗封锁线路和普通性能线路分开管理。',
            '在把变更推向共享设备组之前先准备好 fallback 配置。',
          ],
        },
        {
          title: '把配置调到适合严苛家庭网和移动网',
          paragraphs: [
            'Reality 最有效的时候，通常也是其余配置最“朴素”的时候。除非你有抓包证据，否则不要叠加额外噪声。',
            '当某个地区开始退化时，应按 DNS、TLS 指纹、流量整形逐层排查，而不是一次性乱改所有参数。',
          ],
          bullets: [
            '解析路径尽量与目标地区一致。',
            '在会强制分片的移动运营商上保持保守 MTU。',
            '每次调整后观察连接成功率，而不是只听个别反馈。',
          ],
        },
        {
          title: '把这类线路当成事件响应面来运营',
          paragraphs: [
            '抗封锁不是一次性的 tweak，而是运维问题。每条被封锁的线路都应有明确回滚和可重复的处理流程。',
            '把支持工单、设备类型和丢包观察放到一个运营闭环里，弱线路要尽快淘汰。',
          ],
          bullets: [
            '按 ASN 监控 handshake failure 激增。',
            '在下载包里保留干净的备份路径。',
            '一旦线路轮换，尽快公开状态更新。',
          ],
        },
      ],
      relatedLinks: [
        {
          label: '协议文档',
          href: '/docs',
          description: '在调整客户端预设前先核对底层传输模型。',
        },
        {
          label: '安全姿态',
          href: '/security',
          description: '了解这条线路依赖的加固假设。',
        },
        {
          label: '独立审计',
          href: '/audits',
          description: '查看在信任新线路前应具备哪些证据。',
        },
      ],
      ctaLinks: [
        {
          label: '查看套餐',
          href: '/pricing',
          description: '选择带宽和设备数都足够的套餐。',
          seoCta: 'guide_pricing',
          seoZone: 'guides_content',
        },
        {
          label: '下载客户端',
          href: '/download',
          description: '获取 Android、iOS、桌面端及 sing-box 相关客户端。',
          seoCta: 'guide_download',
          seoZone: 'guides_content',
        },
        {
          label: '打开信任中心',
          href: '/trust',
          description: '查看日志立场、基础设施控制和 abuse 处理方式。',
          seoCta: 'guide_trust',
          seoZone: 'guides_content',
        },
      ],
    },
  },
  'vpn-speed-optimization-for-streaming-and-gaming': {
    'ru-RU': {
      badge: 'Скорость и маршруты',
      title: 'Как ускорить VPN для стриминга и игровых сессий',
      description:
        'Уберите лишнюю задержку, правильно соотнеся протокол, регион выхода и device-level routing с тем трафиком, который для пользователя действительно важен.',
      heroPoints: [
        'Сначала снижайте jitter и очередь, а потом гонитесь за красивыми мегабитами.',
        'Не заставляйте один профиль обслуживать и игры, и тяжёлые загрузки, и весь дом сразу.',
        'Выходной регион должен совпадать с реальным направлением трафика, а не с домашним городом.',
      ],
      sections: [
        {
          title: 'Сначала найдите правильное узкое место',
          paragraphs: [
            'Быстрый VPN для видео не всегда является лучшим VPN для соревновательных игр. Стриминг терпит буфер, игры наказывают за jitter и queue delay.',
            'Прежде чем включать дополнительные клиентские функции, измерьте базовую латентность, packet loss и длину маршрута.',
          ],
        },
        {
          title: 'Сопоставьте протокол с типом нагрузки',
          paragraphs: [
            'WireGuard остаётся отличным выбором, когда приоритетом являются простота и скорость. Reality-профили выигрывают там, где важнее устойчивость к фильтрации.',
            'Оставьте один стабильный preset для консолей и второй для устройств, которые часто прыгают между hostile Wi-Fi и мобильной сетью.',
          ],
          bullets: [
            'По возможности выносите патчи и launcher-трафик в split routing.',
            'Фиксируйте игровой маршрут на ближайшем стабильном egress без вечерней перегрузки.',
            'Не прогоняйте все household-устройства через один high-priority tunnel.',
          ],
        },
        {
          title: 'Превращайте support-сигналы в обновления профилей',
          paragraphs: [
            'Если support регулярно получает жалобы от одного и того же оператора или региона, это уже routing data. Превращайте её в дефолтные профили и рекомендации по download bundle.',
            'Хороший speed guide — это не список магических советов, а operational knowledge, зашитое в выбор клиента и маршрута.',
          ],
        },
      ],
      relatedLinks: [
        {
          label: 'Карта сети',
          href: '/network',
          description: 'Сначала выберите правильный регион, а потом меняйте настройки клиента.',
        },
        {
          label: 'Status page',
          href: '/status',
          description: 'Поймите, локальна ли проблема или маршрут уже известен как деградировавший.',
        },
        {
          label: 'Гайды по устройствам',
          href: '/devices',
          description: 'Соотнесите выбор маршрута с конкретной клиентской платформой.',
        },
      ],
      ctaLinks: [
        {
          label: 'Сравнить тарифы',
          href: '/pricing',
          description: 'Подберите тариф под нужную скорость и количество устройств.',
          seoCta: 'guide_pricing',
          seoZone: 'guides_content',
        },
        {
          label: 'Скачать клиенты',
          href: '/download',
          description: 'Получите клиенты для Android, iOS, desktop и стеков на базе sing-box.',
          seoCta: 'guide_download',
          seoZone: 'guides_content',
        },
        {
          label: 'Открыть trust center',
          href: '/trust',
          description: 'Посмотрите, как описаны логирование, контроль инфраструктуры и эксплуатационные гарантии.',
          seoCta: 'guide_trust',
          seoZone: 'guides_content',
        },
      ],
    },
    'zh-CN': {
      badge: '速度与路由',
      title: '面向流媒体和游戏会话的 VPN 速度优化',
      description:
        '把协议选择、出口地区和设备级路由与实际业务流量对齐，从而减少本可避免的延迟与波动。',
      heroPoints: [
        '先控制抖动和排队延迟，再去追求漂亮的带宽截图。',
        '不要让一个配置同时承载游戏、下载和全家的所有流量。',
        '出口地区应跟真实目标方向一致，而不是机械地贴近用户所在城市。',
      ],
      sections: [
        {
          title: '先确认真正的瓶颈是什么',
          paragraphs: [
            '适合视频的快线路，不一定适合竞技游戏。流媒体能容忍缓冲，而游戏更怕 jitter 和 queue delay。',
            '在改动任何客户端特性之前，先测基础延迟、丢包率和路径距离。',
          ],
        },
        {
          title: '让协议选择与工作负载匹配',
          paragraphs: [
            '如果重点是简单和速度，WireGuard 仍然非常强；如果重点是穿透高压网络，Reality 配置更合适。',
            '为游戏机保留一个稳定 preset，再为经常在 hostile Wi-Fi 和移动网络间切换的设备准备一个 fallback preset。',
          ],
          bullets: [
            '补丁下载和启动器流量尽量走 split routing。',
            '把游戏流量固定到最近且晚高峰拥塞较低的 egress。',
            '不要把全家所有设备都塞进同一条高优先级隧道。',
          ],
        },
        {
          title: '把支持反馈变成默认配置更新',
          paragraphs: [
            '如果支持团队反复收到同一运营商或同一区域的投诉，那已经是路由数据。应把这些信号写回默认 preset 和下载建议。',
            '真正有用的速度指南，不是随机清缓存技巧，而是可落地的运维经验。',
          ],
        },
      ],
      relatedLinks: [
        {
          label: '网络地图',
          href: '/network',
          description: '先选对地区，再调整客户端参数。',
        },
        {
          label: '状态页面',
          href: '/status',
          description: '判断问题是局部故障还是已知线路异常。',
        },
        {
          label: '设备配置',
          href: '/devices',
          description: '把线路选择映射到具体平台与客户端。',
        },
      ],
      ctaLinks: [
        {
          label: '查看套餐',
          href: '/pricing',
          description: '选择满足速度目标和设备数量的套餐。',
          seoCta: 'guide_pricing',
          seoZone: 'guides_content',
        },
        {
          label: '下载客户端',
          href: '/download',
          description: '获取 Android、iOS、桌面端及 sing-box 相关客户端。',
          seoCta: 'guide_download',
          seoZone: 'guides_content',
        },
        {
          label: '打开信任中心',
          href: '/trust',
          description: '查看服务在日志、基础设施控制和运营保证上的公开姿态。',
          seoCta: 'guide_trust',
          seoZone: 'guides_content',
        },
      ],
    },
  },
  'zero-log-vpn-rollout-checklist-for-teams': {
    'ru-RU': {
      badge: 'Запуск и доверие',
      title: 'Чек-лист запуска zero-log VPN для распределённых команд',
      description:
        'Разверните VPN для команды без теневого ИТ, расплывчатых предположений о логировании и слабого device onboarding.',
      heroPoints: [
        'Переводит privacy-claims в реальные правила онбординга и доступа.',
        'Делает настройку устройств предсказуемой ещё до дня запуска.',
        'Считает audit evidence и support playbooks обязательной частью релиза.',
      ],
      sections: [
        {
          title: 'Сведите политику, онбординг и incident response в одну модель',
          paragraphs: [
            'Zero-log обещание ничего не стоит, если support, billing или device history продолжают вытекать лишними метаданными. Проваливается не слоган, а несогласованные operational surfaces.',
            'До первого логина зафиксируйте, кто может вращать ключи, кто видит историю устройств и как обрабатываются потерянные или скомпрометированные устройства.',
          ],
        },
        {
          title: 'Пакуйте rollout по ролям, а не по названиям протоколов',
          paragraphs: [
            'Инженерам, руководителям и полевым сотрудникам не нужен один и тот же набор профилей. Каждой группе дайте минимум чистых presets под её риск-модель.',
            'Чем меньше решений принимает пользователь во время настройки, тем меньше support-боли после запуска.',
          ],
          bullets: [
            'Подготовьте один default route, один fallback для ограниченных сетей и один emergency status link.',
            'К каждому client bundle прикладывайте trust summary и путь эскалации.',
            'Проверьте renewal, downgrade и device-slot политику ещё до пилота.',
          ],
        },
      ],
      relatedLinks: [
        {
          label: 'Trust center',
          href: '/trust',
          description: 'Используйте страницу как краткую сводку гарантий и ограничений для оператора.',
        },
        {
          label: 'Help center',
          href: '/help',
          description: 'База поддержки для настройки, восстановления и эскалации.',
        },
        {
          label: 'Тарифы',
          href: '/pricing',
          description: 'Проверьте экономику устройств и seats до масштабирования rollout.',
        },
      ],
      ctaLinks: [
        {
          label: 'Сравнить тарифы',
          href: '/pricing',
          description: 'Выберите тариф с нужной пропускной способностью и лимитом устройств.',
          seoCta: 'guide_pricing',
          seoZone: 'guides_content',
        },
        {
          label: 'Скачать клиенты',
          href: '/download',
          description: 'Подготовьте Android, iOS, desktop и sing-box based clients к rollout.',
          seoCta: 'guide_download',
          seoZone: 'guides_content',
        },
        {
          label: 'Открыть trust center',
          href: '/trust',
          description: 'Проверьте, как privacy-claims и операционные ограничения описаны публично.',
          seoCta: 'guide_trust',
          seoZone: 'guides_content',
        },
      ],
    },
    'zh-CN': {
      badge: '上线与信任',
      title: '面向分布式团队的 zero-log VPN 上线清单',
      description:
        '在不制造影子 IT、模糊日志假设和脆弱设备 onboarding 的前提下，把 VPN 交付给团队。',
      heroPoints: [
        '把隐私声明转化为实际的 onboarding 与访问控制。',
        '在上线日到来之前先让设备配置过程可预测。',
        '把审计证据和支持手册视为发布条件，而不是附加项。',
      ],
      sections: [
        {
          title: '把政策、onboarding 与 incident response 对齐',
          paragraphs: [
            '如果支持、计费或设备管理流程仍暴露不必要元数据，zero-log 声明本身并没有意义。真正的问题是多个运营面彼此矛盾。',
            '在第一个用户登录之前，先写清谁能轮换密钥、谁能看到设备历史，以及遗失设备如何处理。',
          ],
        },
        {
          title: '按角色打包 rollout，而不是按协议名堆给用户',
          paragraphs: [
            '工程师、管理层和外勤人员需要的 preset 不一样。每一类角色都应得到最少但足够清晰的配置集合。',
            '用户在设置时需要做的决策越少，发布后的支持压力就越低。',
          ],
          bullets: [
            '准备一个默认路由、一个受限网络 fallback，以及一个紧急状态链接。',
            '每个客户端包都配套 trust summary 和支持升级路径。',
            '在试点开始前确认续费、降级和 device slot 政策。',
          ],
        },
      ],
      relatedLinks: [
        {
          label: '信任中心',
          href: '/trust',
          description: '把这里当成团队运营者查看保证与边界的摘要页。',
        },
        {
          label: '帮助中心',
          href: '/help',
          description: '面向终端用户的设置、恢复与支持知识库。',
        },
        {
          label: '套餐页面',
          href: '/pricing',
          description: '在扩大 rollout 之前先核对 seat 和设备成本。',
        },
      ],
      ctaLinks: [
        {
          label: '查看套餐',
          href: '/pricing',
          description: '选择带宽、座席和设备数量都合适的套餐。',
          seoCta: 'guide_pricing',
          seoZone: 'guides_content',
        },
        {
          label: '下载客户端',
          href: '/download',
          description: '为 Android、iOS、桌面端和 sing-box 相关客户端准备 rollout 包。',
          seoCta: 'guide_download',
          seoZone: 'guides_content',
        },
        {
          label: '打开信任中心',
          href: '/trust',
          description: '核对隐私声明和运营边界在公开页面上的表达方式。',
          seoCta: 'guide_trust',
          seoZone: 'guides_content',
        },
      ],
    },
  },
};

export const COMPARISON_DETAIL_LOCALIZATION: Record<string, LocalizedEntryRecord<LocalizedArticleCopy>> = {
  'vless-reality-vs-wireguard': {
    'ru-RU': {
      badge: 'Сравнение протоколов',
      title: 'VLESS Reality vs WireGuard: какой протокол делать основным для VPN-трафика',
      description:
        'Сравните устойчивость к блокировкам и операционную простоту, соотнося каждый протокол с реальными сетями, в которых живут ваши пользователи.',
      heroPoints: [
        'WireGuard остаётся тонким и быстрым в кооперативных сетях.',
        'Reality выигрывает там, где DPI и traffic classification входят в модель угроз.',
        'Правильный выбор зависит от враждебности маршрута, device mix и стоимости поддержки.',
      ],
      sections: [
        {
          title: 'Где WireGuard по-прежнему доминирует',
          paragraphs: [
            'WireGuard отлично подходит, когда главная задача — скорость, предсказуемый roaming и минимальная operational complexity на многих устройствах.',
            'Небольшая поверхность протокола упрощает документацию и снижает риск массовой misconfiguration после онбординга.',
          ],
        },
        {
          title: 'Где VLESS Reality меняет решение',
          paragraphs: [
            'Reality полезен там, где обычный VPN fingerprint сам по себе становится проблемой. Он делает маршрут менее заметным без лишнего театра и шумовых надстроек.',
            'Но эта устойчивость ценна только тогда, когда у вас есть мониторинг target-ов, fallback-пути и документированная ротация.',
          ],
          bullets: [
            'Берите Reality, если hostile network — это норма, а не редкий крайний случай.',
            'Берите WireGuard, если важнее low-friction speed и простое покрытие устройств.',
            'Держите оба варианта, если аудитория делится между обычными и ограниченными сетями.',
          ],
        },
        {
          title: 'Выбирайте default по support-cost, а не по одному бенчмарку',
          paragraphs: [
            'Технически лучший туннель остаётся плохим default, если он умножает setup-failures для основной аудитории. Смотрите на support cost, а не только на сухой benchmark.',
            'Чаще всего побеждает двухполосная стратегия: WireGuard для обычного трафика и Reality для враждебных маршрутов.',
          ],
        },
      ],
      relatedLinks: [
        {
          label: 'Download center',
          href: '/download',
          description: 'Соотнесите выбранный протокол с клиентами и путями установки.',
        },
        {
          label: 'Гайды по устройствам',
          href: '/devices',
          description: 'Выберите setup-flow под конкретную платформу.',
        },
        {
          label: 'Trust center',
          href: '/trust',
          description: 'Поймите операционные гарантии вокруг каждой маршрутной модели.',
        },
      ],
      ctaLinks: [
        {
          label: 'Открыть документацию',
          href: '/docs',
          description: 'Сверьте детали протокола до выбора основного стека.',
          seoCta: 'compare_docs',
          seoZone: 'compare_content',
        },
        {
          label: 'Проверить тарифы',
          href: '/pricing',
          description: 'Соотнесите цели по скорости и количеству устройств с практичным тарифом.',
          seoCta: 'compare_pricing',
          seoZone: 'compare_content',
        },
        {
          label: 'Открыть help center',
          href: '/help',
          description: 'Посмотрите, какие support-поверхности доступны после rollout.',
          seoCta: 'compare_help',
          seoZone: 'compare_content',
        },
      ],
    },
    'zh-CN': {
      badge: '协议对比',
      title: 'VLESS Reality vs WireGuard：默认 VPN 流量应该走哪一个',
      description:
        '把抗审查能力与运维简单性放到真实用户网络环境里比较，决定哪个协议更适合作为默认通道。',
      heroPoints: [
        '在合作性网络里，WireGuard 仍然足够轻量且高效。',
        '如果 DPI 和流量识别属于常态威胁，Reality 更有优势。',
        '正确答案取决于线路敌对程度、设备组合以及支持成本。',
      ],
      sections: [
        {
          title: 'WireGuard 仍然占优的场景',
          paragraphs: [
            '当你的主要问题是速度、稳定 roaming 和跨多设备的简单运维时，WireGuard 依然非常强。',
            '它的表面积小，意味着文档更容易写清楚，用户一旦 onboarding 稳定后也更不容易配错。',
          ],
        },
        {
          title: 'VLESS Reality 改变选择逻辑的场景',
          paragraphs: [
            '如果普通 VPN 指纹本身就会被重点识别，Reality 会更合适。它让线路更难被单独揪出，而不是靠夸张噪声去硬扛。',
            '但这种韧性只有在你准备好 target 监控、fallback 路径和可执行轮换流程时才真正有价值。',
          ],
          bullets: [
            '当 hostile network 是常态而不是边角案例时选 Reality。',
            '当更重要的是 low-friction speed 和广覆盖设备支持时选 WireGuard。',
            '如果用户同时分布在普通和受限网络，两者并存通常最实际。',
          ],
        },
        {
          title: '默认协议应按支持成本决定',
          paragraphs: [
            '技术上更强的隧道，如果会让核心用户群的 setup failure 大幅上升，就不是好 default。应看 support cost，而不是单项 benchmark。',
            '很多时候最稳妥的是双车道策略：普通流量走 WireGuard，敌对线路走 Reality。',
          ],
        },
      ],
      relatedLinks: [
        {
          label: '下载中心',
          href: '/download',
          description: '把选定协议映射到可用客户端和安装路径。',
        },
        {
          label: '设备指南',
          href: '/devices',
          description: '为当前平台选择正确的配置流程。',
        },
        {
          label: '信任中心',
          href: '/trust',
          description: '了解不同线路模型背后的运营保证。',
        },
      ],
      ctaLinks: [
        {
          label: '查看完整文档',
          href: '/docs',
          description: '在选定默认协议栈之前先核对技术细节。',
          seoCta: 'compare_docs',
          seoZone: 'compare_content',
        },
        {
          label: '查看套餐',
          href: '/pricing',
          description: '把性能目标与设备数量映射到实际套餐。',
          seoCta: 'compare_pricing',
          seoZone: 'compare_content',
        },
        {
          label: '打开帮助中心',
          href: '/help',
          description: '查看 rollout 后可用的支持路径。',
          seoCta: 'compare_help',
          seoZone: 'compare_content',
        },
      ],
    },
  },
  'sing-box-vs-clash-meta-for-advanced-routing': {
    'ru-RU': {
      badge: 'Сравнение клиентских стеков',
      title: 'sing-box vs Clash Meta для сложной маршрутизации и контроля fallback',
      description:
        'Сравнение клиентских стеков для пользователей, которым нужны layered routing, чистое распространение профилей и предсказуемое fallback-поведение.',
      heroPoints: [
        'sing-box особенно силён в modern VLESS и Reality-first сценариях.',
        'Clash Meta полезен там, где пользователь реально зависит от rule-heavy workflows.',
        'Неподходящий client stack создаёт скрытый support debt.',
      ],
      sections: [
        {
          title: 'Сначала решите, нужна ли пользователю сложность правил',
          paragraphs: [
            'Если аудитории в основном нужен прямой и стабильный туннель, sing-box оставляет более чистую mental model. Если же люди живут в сетах правил, у Clash Meta до сих пор есть экосистемное преимущество.',
            'Лучшим будет тот стек, который ваши support и docs способны нести без появления новых failure mode.',
          ],
        },
        {
          title: 'Переносимость маршрутов важнее количества фич',
          paragraphs: [
            'Команды часто переоценивают редкие переключатели и недооценивают то, можно ли без сюрпризов перенести один и тот же профиль с телефона на ноутбук.',
            'Выигрывает стек, который позволяет публиковать меньше preset-ов и при этом держать понятное fallback-поведение.',
          ],
          bullets: [
            'Оптимизируйте под воспроизводимость между устройствами.',
            'Избегайте feature-path, который понимает только один support engineer.',
            'Документируйте fallback-маршрут так же строго, как и default.',
          ],
        },
      ],
      relatedLinks: [
        {
          label: 'API и документация',
          href: '/api',
          description: 'Посмотрите, как автоматизация клиента встраивается в выбранный стек.',
        },
        {
          label: 'Status operations',
          href: '/status',
          description: 'Поймите, где пользователь должен смотреть, когда маршрут деградирует.',
        },
        {
          label: 'Security controls',
          href: '/security',
          description: 'Проверьте меры контроля, которые становятся важны после deploy.',
        },
      ],
      ctaLinks: [
        {
          label: 'Открыть документацию',
          href: '/docs',
          description: 'Сверьте детали клиента и протокола до выбора default stack.',
          seoCta: 'compare_docs',
          seoZone: 'compare_content',
        },
        {
          label: 'Проверить тарифы',
          href: '/pricing',
          description: 'Подберите тариф под маршрутизационные цели и объём устройств.',
          seoCta: 'compare_pricing',
          seoZone: 'compare_content',
        },
        {
          label: 'Открыть help center',
          href: '/help',
          description: 'Посмотрите support surface, доступный после rollout.',
          seoCta: 'compare_help',
          seoZone: 'compare_content',
        },
      ],
    },
    'zh-CN': {
      badge: '客户端栈对比',
      title: 'sing-box vs Clash Meta：高级路由与回退控制怎么选',
      description:
        '比较高级用户最常考虑的两类客户端栈，重点放在分层路由、配置下发和可信 fallback 行为上。',
      heroPoints: [
        '在现代 VLESS 与 Reality-first 场景里，sing-box 更自然。',
        '当用户强依赖规则体系时，Clash Meta 依旧有价值。',
        '选错客户端栈会带来难以察觉的支持债务。',
      ],
      sections: [
        {
          title: '先判断用户是否真的需要复杂规则',
          paragraphs: [
            '如果多数用户只需要稳定直连隧道，sing-box 的心智模型更干净；如果他们长期依赖层层规则，Clash Meta 仍有生态优势。',
            '真正好的选择，是你的支持团队和文档体系能稳定承载的那个栈，而不是功能列表更长的那个。',
          ],
        },
        {
          title: '路由可移植性比功能数量更重要',
          paragraphs: [
            '团队往往高估稀有功能，低估同一套配置能否从手机无痛迁移到笔记本。',
            '应优先选择能用更少 preset 覆盖更多设备、并且 fallback 逻辑清晰的客户端栈。',
          ],
          bullets: [
            '围绕跨设备可复现性优化。',
            '避免只有单个支持工程师看得懂的 feature path。',
            '像记录 default route 一样记录 fallback route。',
          ],
        },
      ],
      relatedLinks: [
        {
          label: 'API 与文档',
          href: '/api',
          description: '查看客户端自动化如何接入所选栈。',
        },
        {
          label: '状态运营',
          href: '/status',
          description: '了解当线路退化时用户应查看哪里。',
        },
        {
          label: '安全控制',
          href: '/security',
          description: '检查部署后真正重要的控制面。',
        },
      ],
      ctaLinks: [
        {
          label: '查看完整文档',
          href: '/docs',
          description: '在选择默认客户端栈前先核对技术细节。',
          seoCta: 'compare_docs',
          seoZone: 'compare_content',
        },
        {
          label: '查看套餐',
          href: '/pricing',
          description: '让路由目标与设备规模匹配到合适套餐。',
          seoCta: 'compare_pricing',
          seoZone: 'compare_content',
        },
        {
          label: '打开帮助中心',
          href: '/help',
          description: '查看上线后可用的支持路径。',
          seoCta: 'compare_help',
          seoZone: 'compare_content',
        },
      ],
    },
  },
};

export const DEVICE_DETAIL_LOCALIZATION: Record<string, LocalizedEntryRecord<LocalizedDeviceCopy>> = {
  'android-vpn-setup': {
    'ru-RU': {
      badge: 'Настройка Android',
      title: 'Настройка VPN на Android для ограниченных Wi-Fi и мобильных сетей',
      description:
        'Соберите Android-клиент с устойчивым default route, fallback для агрессивных сетей и понятным переходом от онбординга к day-two support.',
      heroPoints: [
        'Подходит и для обычного мобильного интернета, и для жёсткого public Wi-Fi.',
        'Держит fallback-логику на виду, а не прячет её в неочевидных тумблерах.',
        'Сразу связывает setup с download, support и trust surfaces.',
      ],
      sections: [
        {
          title: 'Сначала выберите правильный клиент',
          paragraphs: [
            'Android-развёртывания ломаются, когда пользователю дают три клиента и предлагают импровизировать. Нужен один рекомендованный клиент и один резервный.',
            'Если пользователь часто попадает в фильтруемые сети, preload-ьте default route и restrictive-network route сразу в стартовый пакет.',
          ],
        },
        {
          title: 'Упакуйте настройку в два чистых preset-а',
          paragraphs: [
            'Первый preset должен быть про скорость и батарею на обычных сетях. Второй — про достижимость, когда сеть становится агрессивной.',
            'Названия профилей должны быть настолько ясными, чтобы support мог понять активный туннель без гадания.',
          ],
          bullets: [
            'Default preset для домашнего broadband и обычного LTE.',
            'Fallback preset для captive portals, кампусных сетей и фильтруемых ISP.',
            'Одна ссылка на trust, одна на help и одна на status.',
          ],
        },
        {
          title: 'Подготовьте day-two support заранее',
          paragraphs: [
            'Android-support становится дорогим, когда единственный playbook — переустановка. Подготовьте recovery flow для просроченных credentials, деградации маршрута и app-specific проблем.',
            'Если команда может объяснить следующий шаг одной фразой, setup уже достаточно зрелый для масштабирования.',
          ],
        },
      ],
      relatedLinks: [
        {
          label: 'Trust center',
          href: '/trust',
          description: 'Дайте пользователю operator-контекст за пределами самой настройки.',
        },
        {
          label: 'Status page',
          href: '/status',
          description: 'Сначала проверьте, известна ли проблема публично, прежде чем менять профиль.',
        },
        {
          label: 'Тарифы',
          href: '/pricing',
          description: 'Убедитесь, что device slots подходят для семьи или команды.',
        },
      ],
      ctaLinks: [
        {
          label: 'Открыть download center',
          href: '/download',
          description: 'Получите правильный client bundle до ручной настройки.',
          seoCta: 'device_download',
          seoZone: 'devices_content',
        },
        {
          label: 'Открыть help center',
          href: '/help',
          description: 'Используйте support docs при онбординге и замене устройства.',
          seoCta: 'device_help',
          seoZone: 'devices_content',
        },
        {
          label: 'Сравнить протоколы',
          href: '/compare',
          description: 'Выберите tunnel model, который соответствует ограничениям устройства.',
          seoCta: 'device_compare',
          seoZone: 'devices_content',
        },
      ],
      featureList: [
        'Fallback-профиль для ограниченных сетей',
        'Preset-ы отдельно для мобильной сети и Wi-Fi',
        'Связка с help, status и trust surfaces для поддержки',
      ],
      offers: [
        {
          name: 'Доступ CyberVPN',
          description: 'Подписка для Android и сценариев с несколькими устройствами.',
          price: '9.99',
          priceCurrency: 'USD',
          url: '/pricing',
        },
      ],
    },
    'zh-CN': {
      badge: 'Android 配置',
      title: '面向受限 Wi-Fi 与移动网络的 Android VPN 配置',
      description:
        '为 Android 客户端准备稳定的默认线路、受限网络 fallback，以及从 onboarding 到后续支持都清晰可执行的配置流程。',
      heroPoints: [
        '同时适用于普通移动网络和高压公共 Wi-Fi。',
        '把 fallback 路径显式展示出来，而不是藏在难找的开关里。',
        '让配置流程直接连接到下载、支持和信任页面。',
      ],
      sections: [
        {
          title: '先安装正确的客户端',
          paragraphs: [
            'Android 配置最容易出问题的原因之一，是用户拿到多个客户端选项后只能自己猜。应先提供一个推荐客户端，再准备一个后备选择。',
            '如果用户经常漫游到过滤网络，应该在一开始就同时下发 default route 和 restrictive-network route。',
          ],
        },
        {
          title: '把配置打包成两个清晰 preset',
          paragraphs: [
            '第一个 preset 应偏向普通网络下的速度和电池表现，第二个则优先确保在激进网络里仍可连通。',
            '配置名称必须足够清楚，让支持团队无需猜测就知道当前用了哪条线路。',
          ],
          bullets: [
            '普通家宽和 LTE 使用的 default preset。',
            '适用于 captive portal、校园网和过滤 ISP 的 fallback preset。',
            '同时附上一条 trust 链接、一条 help 链接和一条 status 链接。',
          ],
        },
        {
          title: '提前准备 day-two support',
          paragraphs: [
            '如果唯一的支持流程就是“重装一次”，Android 运维成本会迅速上升。应准备好针对凭据过期、线路退化和 app-specific 问题的恢复流程。',
            '当团队能够用一句话说清下一步动作时，这套配置才算成熟到可以扩大部署。',
          ],
        },
      ],
      relatedLinks: [
        {
          label: '信任中心',
          href: '/trust',
          description: '让用户理解配置背后的运营上下文。',
        },
        {
          label: '状态页面',
          href: '/status',
          description: '在改动配置前先确认问题是否已被公开记录。',
        },
        {
          label: '套餐页面',
          href: '/pricing',
          description: '在家庭或团队 rollout 前先核对设备数量限制。',
        },
      ],
      ctaLinks: [
        {
          label: '打开下载中心',
          href: '/download',
          description: '在手动配置前先获取正确的客户端包。',
          seoCta: 'device_download',
          seoZone: 'devices_content',
        },
        {
          label: '查看帮助中心',
          href: '/help',
          description: '在 onboarding 或更换设备时使用支持文档。',
          seoCta: 'device_help',
          seoZone: 'devices_content',
        },
        {
          label: '比较协议',
          href: '/compare',
          description: '选择符合设备约束的隧道模型。',
          seoCta: 'device_compare',
          seoZone: 'devices_content',
        },
      ],
      featureList: [
        '受限网络 fallback 配置',
        '分别面向移动数据与 Wi-Fi 的 preset',
        '可直接跳转到 help、status 与 trust 页面',
      ],
      offers: [
        {
          name: 'CyberVPN 访问权限',
          description: '适用于 Android 和多设备路由场景的订阅访问。',
          price: '9.99',
          priceCurrency: 'USD',
          url: '/pricing',
        },
      ],
    },
  },
  'ios-vpn-setup': {
    'ru-RU': {
      badge: 'Настройка iPhone и iPad',
      title: 'Настройка VPN на iOS для стабильного переключения между домом, офисом и хотспотами',
      description:
        'Постройте понятный iOS-маршрут, который переживает смену сети, не увеличивает support churn и даёт пользователю очевидный fallback при деградации.',
      heroPoints: [
        'Фокус на надёжности при переходах между Wi-Fi и cellular.',
        'Fallback flow остаётся очевидным и для support, и для self-serve пользователей.',
        'Инструкции связаны с trust и status-контекстом, а не изолированы.',
      ],
      sections: [
        {
          title: 'Сделайте онбординг коротким настолько, чтобы его реально завершили на телефоне',
          paragraphs: [
            'Мобильный onboarding разваливается, когда он требует терпения desktop-пользователя. Покажите один рекомендуемый клиент, один маршрут и один fallback вместо полной матрицы.',
            'Если инструкция требует постоянного прыгания между приложениями, она не готова к широкому rollout.',
          ],
        },
        {
          title: 'Планируйте деградацию маршрута заранее',
          paragraphs: [
            'iOS-пользователь обвинит приложение раньше, чем сеть. Поэтому нужны status page и backup route, чтобы следующий шаг был очевиден.',
            'Хороший setup guide одновременно является и triage guide.',
          ],
        },
      ],
      relatedLinks: [
        {
          label: 'Download center',
          href: '/download',
          description: 'Начните с рекомендованного клиентского пакета.',
        },
        {
          label: 'Help center',
          href: '/help',
          description: 'Используйте recovery flow, если маршрут перестал работать.',
        },
        {
          label: 'Аудиты',
          href: '/audits',
          description: 'Поймите, какие evidence важны до масштабного deploy.',
        },
      ],
      ctaLinks: [
        {
          label: 'Открыть download center',
          href: '/download',
          description: 'Получите правильный client bundle до настройки.',
          seoCta: 'device_download',
          seoZone: 'devices_content',
        },
        {
          label: 'Открыть help center',
          href: '/help',
          description: 'Используйте support docs для восстановления и замены устройства.',
          seoCta: 'device_help',
          seoZone: 'devices_content',
        },
        {
          label: 'Сравнить протоколы',
          href: '/compare',
          description: 'Выберите tunnel model, который подходит для iOS-сценариев.',
          seoCta: 'device_compare',
          seoZone: 'devices_content',
        },
      ],
      featureList: [
        'Маршруты, устойчивые к смене Wi-Fi и cellular',
        'Видимый путь к status и support эскалации',
        'Планирование fallback-профиля для фильтруемых сетей',
      ],
      offers: [
        {
          name: 'Доступ CyberVPN',
          description: 'Подписка для iPhone, iPad и других классов устройств.',
          price: '9.99',
          priceCurrency: 'USD',
          url: '/pricing',
        },
      ],
    },
    'zh-CN': {
      badge: 'iPhone 与 iPad 配置',
      title: '面向家庭、办公室与公共热点切换的 iOS VPN 配置',
      description:
        '构建一条在网络切换中仍稳定、支持成本可控且在退化时能给用户明确 fallback 的 iOS 路径。',
      heroPoints: [
        '优先保证 Wi-Fi 与蜂窝网络切换时的可靠性。',
        '无论是支持团队还是自助用户，都能快速找到 fallback 流程。',
        '配置说明同时连接 trust 与 status 页面，而不是孤立存在。',
      ],
      sections: [
        {
          title: '让 onboarding 短到足以在手机上完成',
          paragraphs: [
            '移动端 onboarding 失败，往往是因为它假设用户有桌面端的耐心。应给用户一个推荐客户端、一条默认线路和一个 fallback，而不是完整矩阵。',
            '如果说明要求用户频繁切换多个 App，说明流程还没准备好做大规模 rollout。',
          ],
        },
        {
          title: '在问题发生前就规划好线路退化',
          paragraphs: [
            'iOS 用户往往先怪应用，再怪网络。因此必须给他们一条状态页面和一条备份路径，让下一步动作一眼可见。',
            '真正成熟的 setup guide，同时也是一份 triage guide。',
          ],
        },
      ],
      relatedLinks: [
        {
          label: '下载中心',
          href: '/download',
          description: '先获取当前推荐的客户端包。',
        },
        {
          label: '帮助中心',
          href: '/help',
          description: '当线路失效时使用恢复流程。',
        },
        {
          label: '审计页面',
          href: '/audits',
          description: '在广泛部署前先确认应该看哪些证据。',
        },
      ],
      ctaLinks: [
        {
          label: '打开下载中心',
          href: '/download',
          description: '在配置前先获取正确的客户端包。',
          seoCta: 'device_download',
          seoZone: 'devices_content',
        },
        {
          label: '查看帮助中心',
          href: '/help',
          description: '在恢复或更换设备时使用支持文档。',
          seoCta: 'device_help',
          seoZone: 'devices_content',
        },
        {
          label: '比较协议',
          href: '/compare',
          description: '选择最适合 iOS 场景的隧道模型。',
          seoCta: 'device_compare',
          seoZone: 'devices_content',
        },
      ],
      featureList: [
        '面向网络切换的稳定路由配置',
        '可见的 status 与支持升级路径',
        '为过滤网络提前规划 fallback profile',
      ],
      offers: [
        {
          name: 'CyberVPN 访问权限',
          description: '适用于 iPhone、iPad 及其他设备类型的订阅访问。',
          price: '9.99',
          priceCurrency: 'USD',
          url: '/pricing',
        },
      ],
    },
  },
  'windows-vpn-setup': {
    'ru-RU': {
      badge: 'Настройка desktop',
      title: 'Настройка VPN на Windows для рабочих станций, где важны скорость, fallback и ясная поддержка',
      description:
        'Соберите Windows-клиентский путь, который закрывает обычный рабочий трафик, hostile networks и быстрый recovery при смене маршрута или профиля.',
      heroPoints: [
        'Чистый desktop-онбординг для ежедневной работы и поездок.',
        'Понятный переход между default и fallback route.',
        'Рассчитано на меньшее число support escalation после rollout.',
      ],
      sections: [
        {
          title: 'Стандартизируйте клиент и pack профилей',
          paragraphs: [
            'На Windows profile sprawl становится особенно дорогим. Выпускайте один blessed client и строгий profile pack вместо того, чтобы позволять импорт случайных конфигов.',
            'Если пользователь не может понять, какой профиль резервный, упаковка уже слишком расплывчата.',
          ],
        },
        {
          title: 'Считайте rollout рабочих станций полноценной operational surface',
          paragraphs: [
            'Рабочие станции часто первыми показывают проблемы маршрутов, потому что несут более тяжёлый трафик, больше приложений и более жёсткие ожидания.',
            'Связывайте настройку с docs, status visibility и trust context, чтобы пользователи не изобретали собственный troubleshooting path.',
          ],
        },
      ],
      relatedLinks: [
        {
          label: 'API docs',
          href: '/api',
          description: 'Автоматизируйте раздачу маршрутов, если управляете многими seats.',
        },
        {
          label: 'Карта сети',
          href: '/network',
          description: 'Выберите ближайший регион до финализации profile pack.',
        },
        {
          label: 'Trust center',
          href: '/trust',
          description: 'Посмотрите меры контроля за клиентским rollout.',
        },
      ],
      ctaLinks: [
        {
          label: 'Открыть download center',
          href: '/download',
          description: 'Получите правильный desktop client bundle перед настройкой.',
          seoCta: 'device_download',
          seoZone: 'devices_content',
        },
        {
          label: 'Открыть help center',
          href: '/help',
          description: 'Используйте support docs для онбординга и recovery.',
          seoCta: 'device_help',
          seoZone: 'devices_content',
        },
        {
          label: 'Сравнить протоколы',
          href: '/compare',
          description: 'Выберите tunnel model под desktop-нагрузку и ограничения.',
          seoCta: 'device_compare',
          seoZone: 'devices_content',
        },
      ],
      featureList: [
        'Default и fallback профили для рабочих станций',
        'Связка с docs, status и trust surfaces',
        'Понятный выбор маршрута для команд и тяжёлого desktop-трафика',
      ],
      offers: [
        {
          name: 'Доступ CyberVPN',
          description: 'Подписка для Windows и multi-device deployments.',
          price: '9.99',
          priceCurrency: 'USD',
          url: '/pricing',
        },
      ],
    },
    'zh-CN': {
      badge: '桌面端配置',
      title: '面向工作站的 Windows VPN 配置：兼顾速度、fallback 与支持清晰度',
      description:
        '为 Windows 客户端建立一套既覆盖普通办公流量、又能处理 hostile network，并在线路或配置变化时快速恢复的部署路径。',
      heroPoints: [
        '面向日常办公与出差场景的干净桌面 onboarding。',
        '在 default route 与 fallback route 之间切换清晰可控。',
        '目标是在 rollout 后减少支持升级数量。',
      ],
      sections: [
        {
          title: '统一客户端与 profile pack',
          paragraphs: [
            '在 Windows 上，配置散落会变得非常昂贵。应发布一个受控客户端和一套命名严格的 profile pack，而不是让用户导入随机配置。',
            '如果用户自己都看不出哪个配置是备用线路，打包方式就已经过于松散。',
          ],
        },
        {
          title: '把工作站 rollout 当成完整的运营面',
          paragraphs: [
            '工作站通常最先暴露线路问题，因为它们承载更重的流量、更多应用和更高的使用预期。',
            '配置页应同时连接文档、状态可见性和 trust context，避免用户自行发明 troubleshooting 路径。',
          ],
        },
      ],
      relatedLinks: [
        {
          label: 'API 文档',
          href: '/api',
          description: '如果你管理多个座席，可用它自动分发线路。',
        },
        {
          label: '网络地图',
          href: '/network',
          description: '在敲定 profile pack 前先选最近的地区。',
        },
        {
          label: '信任中心',
          href: '/trust',
          description: '查看客户端 rollout 背后的控制措施。',
        },
      ],
      ctaLinks: [
        {
          label: '打开下载中心',
          href: '/download',
          description: '在配置前先获取正确的桌面端客户端包。',
          seoCta: 'device_download',
          seoZone: 'devices_content',
        },
        {
          label: '查看帮助中心',
          href: '/help',
          description: '在 onboarding 与恢复时使用支持文档。',
          seoCta: 'device_help',
          seoZone: 'devices_content',
        },
        {
          label: '比较协议',
          href: '/compare',
          description: '选择适合桌面负载和环境限制的隧道模型。',
          seoCta: 'device_compare',
          seoZone: 'devices_content',
        },
      ],
      featureList: [
        '面向工作站的 default 与 fallback profile',
        '直接连接 docs、status 与 trust 页面',
        '适合团队与重度桌面流量的清晰路由选择',
      ],
      offers: [
        {
          name: 'CyberVPN 访问权限',
          description: '适用于 Windows 和多设备部署场景的订阅访问。',
          price: '9.99',
          priceCurrency: 'USD',
          url: '/pricing',
        },
      ],
    },
  },
};
